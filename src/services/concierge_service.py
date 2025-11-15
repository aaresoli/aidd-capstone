"""
Concierge service that retrieves database context and consults a local LLM.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import os
from pathlib import Path
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from flask import current_app, has_app_context

from datetime import datetime, timedelta, timezone

from src.config import Config
from src.data_access import get_db
from src.data_access.resource_dal import ResourceDAL
from src.data_access.booking_dal import BookingDAL
from src.services.llm_client import LocalLLMClient, LocalLLMUnavailableError
from src.utils.availability import parse_schedule, get_next_available_slot, is_time_in_schedule, parse_time_string


@dataclass(frozen=True)
class ContextChunk:
    source: str
    heading: str
    content: str

    @property
    def preview(self) -> str:
        snippet = self.content.strip()
        if len(snippet) > 200:
            return f"{snippet[:197].rstrip()}..."
        return snippet


class ConciergeService:
    """High-level helper that powers the AI Resource Concierge experience."""

    STOP_WORDS = {
        'the', 'and', 'is', 'a', 'an', 'of', 'to', 'in', 'for', 'with', 'on', 'at',
        'by', 'from', 'or', 'that', 'this', 'these', 'those', 'how', 'what', 'which',
        'can', 'i', 'we', 'about', 'need', 'use', 'it', 'are', 'be', 'do', 'does',
        'me', 'my', 'you', 'your', 'their', 'our', 'any', 'info', 'resource',
        'resources', 'if', 'tell', 'show', 'list'
    }
    MAX_RESOURCES = 4  # Reduced from 6 for faster processing
    MAX_DOC_SNIPPETS = 2  # Reduced from 3 for faster processing

    def __init__(self, *, llm_client: Optional[LocalLLMClient] = None,
                 context_dir: Optional[str] = None) -> None:
        default_root = Path(Config.BASE_DIR).parent / 'docs' / 'context'
        configured = None
        if has_app_context():
            configured = current_app.config.get('CONCIERGE_CONTEXT_DIR')
        self.context_root = Path(context_dir or configured or default_root)
        self.logger = current_app.logger if has_app_context() else logging.getLogger(__name__)
        try:
            self.llm_client = llm_client or LocalLLMClient.from_app_config()
            if self.llm_client:
                self.logger.info('LLM client initialized: %s/%s at %s', 
                               self.llm_client.provider, self.llm_client.model, self.llm_client.base_url)
            else:
                self.logger.info('LLM client not configured (LOCAL_LLM_BASE_URL not set)')
        except Exception as exc:
            self.logger.warning('Failed to initialize LLM client: %s', exc)
            self.llm_client = None

    # Public API --------------------------------------------------------------

    def answer(self, question: str, *,
               category: Optional[str] = None,
               published_only: bool = True) -> Dict:
        """Return an AI-assisted response for the supplied natural language question."""
        cleaned = (question or '').strip()
        if not cleaned:
            raise ValueError('Question must not be empty.')
        if len(cleaned) > 1000:
            raise ValueError('Question must be 1000 characters or fewer.')

        # Detect if this is a greeting/small talk vs. actual resource query
        is_greeting = self._is_greeting_or_small_talk(cleaned)
        
        # Check if this is an availability question
        availability_result = None
        if not is_greeting:
            availability_result = self._check_availability_question(cleaned, published_only=published_only)
        
        keywords = self._extract_keywords(cleaned) or self._tokenize(cleaned)
        
        # Only search for resources if it's not just a greeting and not an availability question
        resources = []
        doc_chunks = []
        if not is_greeting and not availability_result:
            resources = self._resource_matches(cleaned, keywords, category=category, published_only=published_only)
            doc_chunks = self._context_matches(keywords)
        
        # Build stats lazily - only if we have resources (skip for greetings)
        stats = {} if is_greeting else self._build_insights()
        context_block = self._format_context_block(resources, doc_chunks, {})  # Empty stats to skip in context

        # If this is an availability question, return the availability result directly
        if availability_result:
            self.logger.info('Handling as availability question, skipping LLM')
            answer = availability_result
            llm_answer = None
            llm_error = None
        else:
            # Always try to use LLM for intelligent responses
            self.logger.info('Calling LLM for question: %s (has_context: %s)', 
                           cleaned[:50], bool(context_block.strip()))
            llm_answer, llm_error = self._call_llm(cleaned, context_block, is_greeting=is_greeting)
            
            # Use personalized fallback for greetings
            if is_greeting and not llm_answer:
                fallback = "Hello! 👋 I'm your Campus Resource Concierge, and I'm here to help you find the perfect study spaces, maker labs, equipment, and event venues around IU Bloomington. What can I help you discover today?"
            else:
                fallback = self._compose_fallback(resources, doc_chunks, stats)
            
            answer = llm_answer or fallback
            if llm_answer:
                self.logger.info('LLM provided answer (length: %d)', len(llm_answer))
            else:
                self.logger.info('Using fallback response (LLM unavailable or returned empty)')

        return {
            'question': cleaned,
            'answer': answer,
            'resources': [self._serialize_resource(resource) for resource in resources] if not is_greeting else [],
            'doc_snippets': [self._serialize_chunk(chunk) for chunk in doc_chunks],
            'stats': stats,
            'used_llm': llm_answer is not None,
            'llm_error': llm_error,
            'context_block': context_block
        }

    # Retrieval helpers -------------------------------------------------------

    def _context_matches(self, keywords: Sequence[str]) -> List[ContextChunk]:
        chunks = self._load_context_chunks(self.context_root)
        scored: List[Tuple[float, ContextChunk]] = []
        for chunk in chunks:
            score = self._score_text(chunk.content, keywords, heading=chunk.heading)
            if score <= 0:
                continue
            scored.append((score, chunk))

        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[: self.MAX_DOC_SNIPPETS]]

    def _resource_matches(self, question: str, keywords: Sequence[str], *,
                          category: Optional[str], published_only: bool) -> List:
        tokens = list(keywords) if keywords else self._tokenize(question)
        filtered_terms = [
            token for token in tokens
            if token and token not in self.STOP_WORDS
        ]
        if not filtered_terms:
            filtered_terms = [token for token in self._tokenize(question) if token]

        scored: Dict[int, Tuple[float, object]] = {}
        status_filter = 'published' if published_only else None

        # Detect category from question if not explicitly provided
        detected_category = category
        if not detected_category:
            question_lower = question.lower()
            category_keywords = {
                'Study Room': ['study', 'study room', 'study space', 'quiet', 'reading', 'library'],
                'Lab Equipment': ['lab', 'laboratory', 'equipment', 'scientific', 'research', 'experiment'],
                'Event Space': ['event', 'venue', 'meeting', 'conference', 'presentation', 'gathering', 'auditorium', 'hall'],
                'AV Equipment': ['av', 'audio', 'video', 'microphone', 'projector', 'sound', 'recording', 'podcast', 'studio', 'broadcast'],
                'Tutoring': ['tutor', 'tutoring', 'help', 'academic support', 'academic help']
            }
            for cat, keywords_list in category_keywords.items():
                if any(kw in question_lower for kw in keywords_list):
                    detected_category = cat
                    break

        # Optimized: Use the full question for a single search instead of multiple term searches
        # This reduces database queries from up to 5 to just 1-2
        if filtered_terms:
            # First, try searching with category filter if detected
            rows = ResourceDAL.search_resources(
                keyword=question,  # Use full question for better context matching
                category=detected_category,  # Use detected category to filter results
                status=status_filter,
                per_page=self.MAX_RESOURCES * 4,  # Get more candidates in one query
                page=1
            ) or []
            
            # Score all results at once with minimum threshold
            for resource in rows:
                if resource.resource_id in scored:
                    continue
                score = self._score_resource(resource, filtered_terms)
                # Only include resources with meaningful relevance (minimum threshold)
                if score >= 1.0:  # Require at least some relevance
                    scored[resource.resource_id] = (score, resource)
            
            # If we have a strong title match but no category match, also search without category filter
            # This handles cases like "podcast room" where title matches but category might not
            if detected_category and len(scored) < 2:
                # Check if we have strong title matches that might be in different categories
                rows_no_category = ResourceDAL.search_resources(
                    keyword=question,
                    category=None,  # Search all categories
                    status=status_filter,
                    per_page=self.MAX_RESOURCES * 6,
                    page=1
                ) or []
                
                for resource in rows_no_category:
                    if resource.resource_id in scored:
                        continue
                    score = self._score_resource(resource, filtered_terms)
                    # For title-based matches, be more lenient if title matches strongly
                    title = (getattr(resource, 'title', None) or '').lower()
                    has_strong_title_match = any(
                        keyword in title and len(keyword) >= 4 
                        for keyword in filtered_terms
                    )
                    # Include if strong title match (even if category doesn't match) or good overall score
                    if has_strong_title_match and score >= 2.0:
                        scored[resource.resource_id] = (score, resource)

        if scored:
            ranked = sorted(scored.values(), key=lambda item: item[0], reverse=True)
            # Only return top results that meet a quality threshold
            # If top result has high score, be more selective
            top_score = ranked[0][0] if ranked else 0
            if top_score >= 5.0:
                # High-quality matches - only return very relevant ones
                threshold = max(2.0, top_score * 0.3)  # At least 30% of top score
                filtered = [(s, r) for s, r in ranked if s >= threshold]
                return [resource for _, resource in filtered[: self.MAX_RESOURCES]]
            else:
                # Lower quality matches - return best available
                return [resource for _, resource in ranked[: self.MAX_RESOURCES]]

        # Fallback: get some resources if no matches
        fallback = ResourceDAL.search_resources(
            keyword=None,
            category=category,
            status=status_filter,
            per_page=self.MAX_RESOURCES,
            page=1
        )
        return fallback or []

    # Prompt + completion helpers --------------------------------------------

    def _call_llm(self, question: str, context_block: str, *, is_greeting: bool = False) -> Tuple[Optional[str], Optional[str]]:
        if not self.llm_client:
            self.logger.info('LLM client not available - using fallback summary')
            return None, 'Local AI runtime is not configured.'

        self.logger.info('Calling LLM with question: %s', question[:50])
        
        if is_greeting:
            # Friendly greeting response with personality
            system_prompt = (
                "You are a friendly and helpful Campus Resource Concierge for Indiana University Bloomington. "
                "You're enthusiastic about helping students, faculty, and staff find the perfect campus resources. "
                "Respond warmly to greetings and small talk. Be conversational, friendly, and show genuine interest. "
                "Mention that you can help them find study rooms, maker spaces, equipment, event venues, and more. "
                "Keep it brief (2-3 sentences) and inviting. Use a warm, approachable tone. "
                "Write in clear, well-formatted paragraphs with proper spacing."
            )
            user_prompt = question.strip()
        else:
            # Intelligent response that can handle both resource questions and general questions
            has_context = context_block.strip() and context_block.strip() != "RESOURCES: None found."
            
            if has_context:
                system_prompt = (
                    "You are a knowledgeable and friendly Campus Resource Concierge for Indiana University Bloomington. "
                    "You help students, faculty, and staff with campus resources and general questions about IU Bloomington. "
                    "You're enthusiastic, helpful, and genuinely want to make their campus experience better. "
                    "\n"
                    "When answering questions about campus resources:\n"
                    "- Use the CONTEXT below which contains relevant resources and documentation\n"
                    "- Only mention resources from the CONTEXT that are ACTUALLY relevant to the question\n"
                    "- If the user asks for 'study rooms', only mention resources in the 'Study Room' category\n"
                    "- If they ask for 'lab equipment', only mention 'Lab Equipment' resources\n"
                    "- Do NOT mention resources from unrelated categories\n"
                    "- Mention resources naturally using **bold** for resource names and explain why they're helpful\n"
                    "\n"
                    "When answering general questions (not about specific resources):\n"
                    "- Use your knowledge about Indiana University Bloomington, campus life, and general topics\n"
                    "- Be helpful, accurate, and conversational\n"
                    "- If you don't know something, admit it and suggest where they might find the information\n"
                    "- You can answer questions about campus services, student life, academic programs, facilities, etc.\n"
                    "\n"
                    "Always:\n"
                    "- Be conversational and engaging (3-5 sentences for simple questions, more for complex topics)\n"
                    "- Show personality while staying accurate and helpful\n"
                    "- Format your response with clear paragraphs, proper spacing, and use **bold** for important names or key terms\n"
                    "- If the CONTEXT doesn't contain relevant resources but the question is about resources, be honest and suggest they try rephrasing"
                )
                user_prompt = f"{question.strip()}\n\nCONTEXT:\n{context_block.strip()}"
            else:
                # No context available - answer general questions intelligently
                system_prompt = (
                    "You are a knowledgeable and friendly Campus Resource Concierge for Indiana University Bloomington. "
                    "You help students, faculty, and staff with questions about IU Bloomington, campus resources, student life, and general topics. "
                    "You're enthusiastic, helpful, and genuinely want to make their campus experience better. "
                    "\n"
                    "Answer the user's question to the best of your ability. You can discuss:\n"
                    "- Campus resources and facilities\n"
                    "- Student life and services\n"
                    "- Academic programs and departments\n"
                    "- Campus locations and buildings\n"
                    "- General questions about IU Bloomington\n"
                    "- General knowledge questions (when appropriate)\n"
                    "\n"
                    "Guidelines:\n"
                    "- Be conversational, helpful, and engaging\n"
                    "- If you don't know something specific, admit it and suggest where they might find the information\n"
                    "- Use **bold** for important names, locations, or key terms\n"
                    "- Format your response with clear paragraphs and proper spacing\n"
                    "- Keep responses appropriate in length (3-5 sentences for simple questions, more for complex topics)"
                )
                user_prompt = question.strip()
        
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            answer = self.llm_client.chat(messages)
            self.logger.info('LLM response received (length: %d)', len(answer))
            # Clean up and format the response
            answer = self._format_response(answer)
            return answer, None
        except LocalLLMUnavailableError as exc:
            self.logger.warning('Local AI unavailable: %s', exc)
            return None, str(exc)

    def _compose_fallback(self, resources: Sequence, doc_chunks: Sequence[ContextChunk],
                          stats: Dict) -> str:
        """Compose a well-formatted fallback response when LLM is unavailable."""
        segments: List[str] = []

        if resources:
            intro = f"I found {len(resources)} resource{'s' if len(resources) != 1 else ''} that might help:"
            segments.append(intro)
            
            for resource in resources:
                title = getattr(resource, 'title', 'Unknown')
                category = getattr(resource, 'category', None) or 'General'
                location = getattr(resource, 'location', None) or 'Location TBD'
                capacity = getattr(resource, 'capacity', None)
                desc = (getattr(resource, 'description', None) or '').strip()
                
                resource_info = f"• **{title}** ({category})"
                if location and location != 'Location TBD':
                    resource_info += f" — located at {location}"
                if capacity:
                    resource_info += f" — {capacity} seats"
                
                if desc:
                    # Truncate description to first sentence or 120 chars
                    first_sentence = desc.split('.')[0]
                    if len(first_sentence) > 120:
                        first_sentence = first_sentence[:117] + '...'
                    resource_info += f"\n  {first_sentence}"
                
                segments.append(resource_info)
        else:
            # For general questions without resources, provide a helpful message
            segments.append(
                "I'm here to help! However, I couldn't find specific resources matching your question in the current catalog. "
                "You can ask me about:\n\n"
                "• **Campus resources** - study rooms, labs, equipment, event spaces\n"
                "• **General questions** - campus services, student life, facilities\n"
                "• **Availability** - check if specific resources are available now\n\n"
                "Try rephrasing your question or ask about something else!"
            )

        if stats.get('most_requested'):
            segments.append("\nHere are some popular resources that might interest you:")
            for item in stats['most_requested']:
                segments.append(f"• {item['title']} ({item['total']} recent bookings)")

        return "\n\n".join(segments)

    def _format_context_block(self, resources: Sequence, doc_chunks: Sequence[ContextChunk],
                              stats: Dict) -> str:
        """Format context block in a compact way to reduce prompt size."""
        lines: List[str] = []
        if resources:
            lines.append("RESOURCES:")
            for resource in resources:
                # More compact format - shorter descriptions
                description = (getattr(resource, 'description', None) or '')[:100].strip()
                desc_text = description + ('…' if len(getattr(resource, 'description', None) or '') > 100 else '')
                lines.append(
                    f"- {getattr(resource, 'title', 'Unknown')} ({getattr(resource, 'category', None) or 'General'}) | "
                    f"{getattr(resource, 'location', None) or 'TBD'} | "
                    f"Cap:{getattr(resource, 'capacity', None) or 'varies'} | "
                    f"{'Approval req' if getattr(resource, 'is_restricted', False) else 'Auto'} | "
                    f"{desc_text}"
                )
        else:
            lines.append("RESOURCES: None found.")

        # Skip stats to reduce context size - they're not critical for most queries
        if doc_chunks:
            lines.append("DOCS:")
            for chunk in doc_chunks:
                # Shorter preview
                preview = chunk.preview[:120] + ('…' if len(chunk.preview) > 120 else '')
                lines.append(f"- {chunk.heading}: {preview}")

        return "\n".join(lines)

    # Statistical context ----------------------------------------------------

    def _build_insights(self) -> Dict:
        """Build lightweight insights - only essential stats to reduce query overhead."""
        # Only get most requested (most useful for fallback), skip others for speed
        return {
            'most_requested': self._most_requested_resources(limit=2),  # Reduced from 3
            'category_counts': [],  # Skip - not critical for responses
            'total_resources': 0  # Skip - not critical for responses
        }

    @staticmethod
    def _most_requested_resources(limit: int = 3) -> List[Dict[str, object]]:
        query = '''
            SELECT r.resource_id,
                   r.title,
                   COUNT(b.booking_id) AS total
            FROM bookings b
            JOIN resources r ON r.resource_id = b.resource_id
            WHERE b.status IN ('pending', 'approved', 'completed')
            GROUP BY r.resource_id, r.title
            ORDER BY total DESC
            LIMIT ?
        '''
        with get_db() as conn:
            cursor = conn.cursor()
            rows = cursor.execute(query, (limit,)).fetchall()
        return [dict(row) for row in rows]

    # Serialization helpers --------------------------------------------------

    @staticmethod
    def _serialize_resource(resource) -> Dict:
        return {
            'resource_id': getattr(resource, 'resource_id', None),
            'title': getattr(resource, 'title', 'Unknown'),
            'category': getattr(resource, 'category', None),
            'location': getattr(resource, 'location', None),
            'description': getattr(resource, 'description', None) or '',
            'capacity': getattr(resource, 'capacity', None),
            'is_restricted': getattr(resource, 'is_restricted', False),
            'equipment': getattr(resource, 'equipment', None),
            'rating': getattr(resource, 'avg_rating', None),
            'status': getattr(resource, 'status', 'draft')
        }

    @staticmethod
    def _serialize_chunk(chunk: ContextChunk) -> Dict:
        return {
            'source': chunk.source,
            'heading': chunk.heading,
            'preview': chunk.preview,
            'content': chunk.content.strip()
        }

    # Response formatting ------------------------------------------------------

    def _format_response(self, text: str) -> str:
        """Clean up and format LLM response for better display."""
        if not text:
            return text
        
        # Remove excessive whitespace
        lines = [line.strip() for line in text.split('\n')]
        
        # Remove empty lines at start/end
        while lines and not lines[0]:
            lines.pop(0)
        while lines and not lines[-1]:
            lines.pop()
        
        # Join with proper spacing (single blank line between paragraphs)
        formatted = []
        prev_empty = False
        for line in lines:
            if not line:
                if not prev_empty:
                    formatted.append('')
                prev_empty = True
            else:
                formatted.append(line)
                prev_empty = False
        
        return '\n'.join(formatted)

    # Availability checking ----------------------------------------------------

    def _check_availability_question(self, question: str, *, published_only: bool = True) -> Optional[str]:
        """
        Check if the question is asking about availability and return a response.
        Returns None if not an availability question, otherwise returns the answer.
        
        This should only trigger for specific availability questions about named resources.
        """
        question_lower = question.lower().strip()
        
        # More specific patterns that indicate availability questions about specific resources
        # These patterns require a resource name to be present
        availability_patterns = [
            r'is\s+(?:the\s+)?(.+?)\s+available\s+now\??',  # "is the auditorium available now?"
            r'is\s+(?:the\s+)?(.+?)\s+available\s+right\s+now\??',  # "is the auditorium available right now?"
            r'when\s+is\s+(?:the\s+)?(.+?)\s+available\??',  # "when is the auditorium available?"
            r'when\s+can\s+i\s+book\s+(?:the\s+)?(.+?)\??',  # "when can I book the auditorium?"
            r'next\s+available\s+(?:slot|time)\s+for\s+(?:the\s+)?(.+?)\??',  # "next available slot for the auditorium"
            r'(.+?)\s+available\s+now\??',  # "auditorium available now?"
        ]
        
        resource_name = None
        matched_pattern = None
        
        for pattern in availability_patterns:
            match = re.search(pattern, question_lower)
            if match:
                potential_name = match.group(1).strip()
                # Remove common trailing words that aren't part of the resource name
                potential_name = re.sub(r'\s+(now|today|tomorrow|this\s+week|right\s+now)$', '', potential_name)
                
                # Only proceed if we have a meaningful resource name (at least 3 chars, not just common words)
                if len(potential_name) >= 3 and potential_name not in ['it', 'this', 'that', 'there', 'here']:
                    resource_name = potential_name
                    matched_pattern = pattern
                    break
        
        if not resource_name:
            return None  # Not a specific availability question, let LLM handle it
        
        # Search for the resource
        resources = ResourceDAL.search_resources(
            keyword=resource_name,
            status='published' if published_only else None,
            per_page=5,
            page=1
        ) or []
        
        # Only handle availability if we found a matching resource
        # Otherwise, let it go through normal LLM flow so it can answer intelligently
        if not resources:
            return None  # Resource not found, let LLM answer (might be a general question)
        
        # Use the first/best matching resource
        resource = resources[0]
        
        # Check current availability
        # Use UTC for database comparisons, but convert to local for schedule checks
        from src.utils.datetime_helpers import get_timezone
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        local_tz = get_timezone(Config.TIMEZONE)
        now_local = datetime.now(local_tz).replace(tzinfo=None)
        
        # Get all active bookings for this resource
        bookings = BookingDAL.get_bookings_by_resource(resource.resource_id)
        active_bookings = []
        for b in bookings:
            if b.status not in ('pending', 'approved'):
                continue
            end_dt = b.end_datetime
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt)
            # Compare in UTC since bookings are stored in UTC
            if end_dt > now_utc:
                active_bookings.append(b)
        
        # Parse schedule
        schedule = parse_schedule(getattr(resource, 'availability_schedule', None))
        
        # Check if resource is available right now
        is_available_now = True
        conflict_reason = None
        
        # Check if within operating hours (use local time for schedule)
        if schedule:
            if not is_time_in_schedule(now_local, schedule):
                is_available_now = False
                conflict_reason = "The resource is currently outside its operating hours."
        
        # Check for booking conflicts (use UTC for booking comparisons)
        if is_available_now:
            for booking in active_bookings:
                start_dt = booking.start_datetime
                end_dt = booking.end_datetime
                
                if isinstance(start_dt, str):
                    start_dt = datetime.fromisoformat(start_dt)
                if isinstance(end_dt, str):
                    end_dt = datetime.fromisoformat(end_dt)
                
                # Check if current time overlaps with booking (compare in UTC)
                if start_dt <= now_utc < end_dt:
                    is_available_now = False
                    conflict_reason = f"The resource is currently booked until {self._format_datetime(end_dt)}."
                    break
        
        # Format response
        if is_available_now:
            response = f"✅ Yes! **{resource.title}** is available right now."
            if schedule:
                # Check when it closes today (use local time)
                day_name = now_local.strftime('%A').lower()
                day_schedule = schedule.get(day_name, [])
                if day_schedule:
                    latest_close = None
                    for window in day_schedule:
                        end_time_str = window.get('end', '23:59')
                        end_time = parse_time_string(end_time_str)
                        if end_time:
                            close_dt = datetime.combine(now_local.date(), end_time)
                            if latest_close is None or close_dt > latest_close:
                                latest_close = close_dt
                    if latest_close and latest_close > now_local:
                        response += f" It's open until {self._format_datetime(latest_close)} today."
        else:
            response = f"❌ **{resource.title}** is not available right now."
            if conflict_reason:
                response += f" {conflict_reason}"
            
            # Find next available slot
            next_slot = self._find_next_available_slot(resource, active_bookings, schedule)
            if next_slot:
                response += f"\n\n📅 The next available slot is {self._format_datetime(next_slot)}."
            else:
                response += "\n\nI couldn't find an available slot in the next 7 days. Please check back later or contact the resource owner."
        
        return response
    
    def _find_next_available_slot(self, resource, active_bookings, schedule) -> Optional[datetime]:
        """Find the next available slot for a resource."""
        if not schedule:
            # No schedule defined, can't determine availability
            return None
        
        # Use UTC for database comparisons
        from src.utils.datetime_helpers import get_timezone
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        local_tz = get_timezone(Config.TIMEZONE)
        now_local = datetime.now(local_tz).replace(tzinfo=None)
        
        # Get resource booking parameters
        duration_minutes = getattr(resource, 'min_booking_minutes', 60) or 60
        buffer_minutes = getattr(resource, 'buffer_minutes', 0) or 0
        lead_time_hours = getattr(resource, 'min_lead_time_hours', 0) or 0
        increment_minutes = getattr(resource, 'booking_increment_minutes', 30) or 30
        
        # Convert bookings to format expected by get_next_available_slot
        # get_next_available_slot expects UTC times but uses local time for schedule checks
        booking_list = []
        for booking in active_bookings:
            start_dt = booking.start_datetime
            end_dt = booking.end_datetime
            
            if isinstance(start_dt, str):
                start_dt = datetime.fromisoformat(start_dt)
            if isinstance(end_dt, str):
                end_dt = datetime.fromisoformat(end_dt)
            
            # Only include future bookings (compare in UTC)
            if end_dt > now_utc:
                booking_list.append(booking)
        
        # get_next_available_slot handles timezone conversion internally
        # It expects UTC start_from but converts to local for schedule checks
        return get_next_available_slot(
            schedule=schedule,
            existing_bookings=booking_list,
            duration_minutes=duration_minutes,
            buffer_minutes=buffer_minutes,
            start_from=now_utc,  # Pass UTC time
            lead_time_hours=lead_time_hours,
            max_days_ahead=7,
            increment_minutes=increment_minutes
        )
    
    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display in availability responses."""
        from src.utils.datetime_helpers import get_timezone
        local_tz = get_timezone(Config.TIMEZONE)
        
        # Convert UTC to local time
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        dt_local = dt.astimezone(local_tz).replace(tzinfo=None)
        
        now_local = datetime.now(local_tz).replace(tzinfo=None)
        
        # Format based on how far in the future
        if dt_local.date() == now_local.date():
            # Today
            return f"today at {dt_local.strftime('%I:%M %p').lstrip('0')}"
        elif dt_local.date() == (now_local.date() + timedelta(days=1)):
            # Tomorrow
            return f"tomorrow at {dt_local.strftime('%I:%M %p').lstrip('0')}"
        else:
            # Future date
            return dt_local.strftime('%A, %B %d at %I:%M %p').lstrip('0')

    # Question classification --------------------------------------------------

    def _is_greeting_or_small_talk(self, question: str) -> bool:
        """Detect if the question is a greeting or small talk rather than a resource query."""
        question_lower = question.lower().strip()
        
        # Common greetings and small talk patterns
        greeting_patterns = [
            'hi', 'hello', 'hey', 'greetings', 'good morning', 'good afternoon', 'good evening',
            'how are you', 'what\'s up', 'sup', 'howdy', 'hi there', 'hello there',
            'thanks', 'thank you', 'bye', 'goodbye', 'see you', 'nice to meet you'
        ]
        
        # Check if it's just a greeting (very short and matches patterns)
        if len(question_lower.split()) <= 3:
            for pattern in greeting_patterns:
                if pattern in question_lower:
                    return True
        
        # Check if it's a question about the AI itself (not resources)
        ai_self_patterns = [
            'who are you', 'what are you', 'what can you do', 'how do you work',
            'tell me about yourself', 'what is this', 'what is concierge'
        ]
        for pattern in ai_self_patterns:
            if pattern in question_lower:
                return True
        
        return False

    # Tokenization + scoring --------------------------------------------------

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords with category awareness."""
        tokens = self._tokenize(text)
        keywords = [
            token for token in tokens
            if token not in self.STOP_WORDS and len(token) >= 2
        ]
        
        # Expand common terms to their full category names
        category_expansions = {
            'study': 'study room',
            'room': 'study room',
            'lab': 'lab equipment',
            'equipment': 'lab equipment',
            'event': 'event space',
            'space': 'event space',
            'av': 'av equipment',
            'audio': 'av equipment',
            'video': 'av equipment',
            'podcast': 'podcast recording studio',
            'recording': 'recording studio',
            'studio': 'recording studio',
            'tutor': 'tutoring',
            'tutoring': 'tutoring'
        }
        
        expanded = []
        for token in keywords:
            if token in category_expansions:
                # Add both the token and expanded form
                expanded.append(token)
                expanded_category = category_expansions[token]
                expanded.extend(expanded_category.split())
            else:
                expanded.append(token)
        
        # Remove duplicates while preserving order
        seen = set()
        ordered = []
        for token in expanded:
            if token in seen:
                continue
            seen.add(token)
            ordered.append(token)
        return ordered

    @staticmethod
    def _tokenize(text: str) -> List[str]:
        return re.findall(r'[a-z0-9]+', text.lower())

    def _score_text(self, text: str, keywords: Sequence[str], *, heading: str = '') -> float:
        if not text:
            return 0.0
        haystack = text.lower()
        heading_tokens = heading.lower()
        score = 0.0
        for keyword in keywords:
            occurrences = haystack.count(keyword)
            if occurrences:
                score += 1.0 + 0.5 * (occurrences - 1)
            if keyword in heading_tokens:
                score += 0.5
        return score

    def _score_resource(self, resource, keywords: Sequence[str]) -> float:
        """Score a resource based on keyword relevance with category weighting."""
        score = 0.0
        category = (getattr(resource, 'category', None) or '').lower()
        title = (getattr(resource, 'title', None) or '').lower()
        description = (getattr(resource, 'description', None) or '').lower()
        
        # Category matching gets highest weight (most important for relevance)
        for keyword in keywords:
            if keyword in category:
                score += 5.0  # Strong category match
            # Partial category match (e.g., "study" matches "Study Room")
            if len(keyword) >= 4 and keyword in category:
                score += 3.0
        
        # Title matching gets high weight
        for keyword in keywords:
            if keyword in title:
                score += 3.0
                # Exact title match is even better
                if title == keyword or title.startswith(keyword + ' ') or title.endswith(' ' + keyword):
                    score += 2.0
        
        # Description matching gets moderate weight
        for keyword in keywords:
            if keyword in description:
                score += 1.0
        
        # Equipment and location get lower weight
        equipment = (getattr(resource, 'equipment', None) or '').lower()
        location = (getattr(resource, 'location', None) or '').lower()
        for keyword in keywords:
            if keyword in equipment:
                score += 0.5
            if keyword in location:
                score += 0.5
        
        return score

    # Context loading --------------------------------------------------------

    @classmethod
    @lru_cache(maxsize=1)
    def _load_context_chunks(cls, root: Path) -> Tuple[ContextChunk, ...]:
        chunks: List[ContextChunk] = []
        if not root.exists():
            return tuple()

        for filepath in sorted(root.rglob('*.md')):
            try:
                text = filepath.read_text(encoding='utf-8')
            except OSError:
                continue
            rel_path = os.path.relpath(filepath, root)
            chunks.extend(cls._split_markdown_into_chunks(text, rel_path))
        return tuple(chunks)

    @staticmethod
    def _split_markdown_into_chunks(text: str, source: str) -> List[ContextChunk]:
        chunks: List[ContextChunk] = []
        current_heading = None
        current_lines: List[str] = []

        def push_chunk():
            content = '\n'.join(current_lines).strip()
            if not content:
                return
            heading = current_heading or 'Overview'
            chunks.append(ContextChunk(source=source, heading=heading, content=content))

        for line in text.splitlines():
            heading_match = re.match(r'^\s{0,3}#{1,6}\s+(.*)', line)
            if heading_match:
                if current_lines:
                    push_chunk()
                    current_lines.clear()
                current_heading = heading_match.group(1).strip()
                continue
            current_lines.append(line)

        if current_lines:
            push_chunk()

        if not chunks:
            cleaned = text.strip()
            if cleaned:
                chunks.append(ContextChunk(source=source, heading='Overview', content=cleaned))
        return chunks
