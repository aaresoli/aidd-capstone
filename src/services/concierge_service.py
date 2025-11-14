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

from src.config import Config
from src.data_access import get_db
from src.data_access.resource_dal import ResourceDAL
from src.services.llm_client import LocalLLMClient, LocalLLMUnavailableError


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
    MAX_RESOURCES = 6
    MAX_DOC_SNIPPETS = 3

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

        keywords = self._extract_keywords(cleaned) or self._tokenize(cleaned)
        resources = self._resource_matches(cleaned, keywords, category=category, published_only=published_only)
        doc_chunks = self._context_matches(keywords)
        stats = self._build_insights()
        context_block = self._format_context_block(resources, doc_chunks, stats)

        llm_answer, llm_error = self._call_llm(cleaned, context_block)
        fallback = self._compose_fallback(resources, doc_chunks, stats)
        answer = llm_answer or fallback

        return {
            'question': cleaned,
            'answer': answer,
            'resources': [self._serialize_resource(resource) for resource in resources],
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

        for term in filtered_terms[:5]:
            rows = ResourceDAL.search_resources(
                keyword=term,
                category=category,
                status=status_filter,
                per_page=self.MAX_RESOURCES * 3,
                page=1
            ) or []
            for resource in rows:
                if resource.resource_id in scored:
                    continue
                score = self._score_resource(resource, filtered_terms)
                if score <= 0:
                    continue
                scored[resource.resource_id] = (score, resource)

        if scored:
            ranked = sorted(scored.values(), key=lambda item: item[0], reverse=True)
            return [resource for _, resource in ranked[: self.MAX_RESOURCES]]

        fallback = ResourceDAL.search_resources(
            keyword=None,
            category=category,
            status=status_filter,
            per_page=self.MAX_RESOURCES,
            page=1
        )
        return fallback or []

    # Prompt + completion helpers --------------------------------------------

    def _call_llm(self, question: str, context_block: str) -> Tuple[Optional[str], Optional[str]]:
        if not self.llm_client:
            return None, 'Local AI runtime is not configured.'

        system_prompt = (
            "You are the Campus Resource Concierge for Indiana University Bloomington. "
            "You MUST answer ONLY using the information provided in the CONTEXT section below. "
            "DO NOT use any external knowledge, web searches, or information not explicitly provided in the CONTEXT. "
            "If the CONTEXT does not contain the answer, explicitly state that the information is not available in the database. "
            "Never invent, guess, or make up resources, policies, availability, or any other details. "
            "If data is missing, admit it clearly and offer only the closest matching details from the CONTEXT."
        )
        user_prompt = f"{question.strip()}\n\nCONTEXT:\n{context_block.strip()}"
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ]

        try:
            answer = self.llm_client.chat(messages)
            return answer, None
        except LocalLLMUnavailableError as exc:
            self.logger.warning('Local AI unavailable: %s', exc)
            return None, str(exc)

    def _compose_fallback(self, resources: Sequence, doc_chunks: Sequence[ContextChunk],
                          stats: Dict) -> str:
        segments: List[str] = []

        if resources:
            resource_lines = [
                f"- {getattr(resource, 'title', 'Unknown')} ({getattr(resource, 'category', None) or 'General'}) · "
                f"{getattr(resource, 'location', None) or 'Location TBD'} · "
                f"{getattr(resource, 'capacity', None) or 'capacity varies'} seats · "
                f"{'requires approval' if getattr(resource, 'is_restricted', False) else 'auto-approves'}"
                for resource in resources
            ]
            segments.append("Closest matches from the resource catalog:\n" + "\n".join(resource_lines))
        else:
            segments.append("No matching resources were found in the current catalog for that question.")

        if stats.get('most_requested'):
            lines = [
                f"- {item['title']} ({item['total']} recent bookings)"
                for item in stats['most_requested']
            ]
            segments.append("Most requested resources by bookings:\n" + "\n".join(lines))

        if doc_chunks:
            doc_lines = [
                f"- {chunk.heading} ({chunk.source}): {chunk.preview}"
                for chunk in doc_chunks
            ]
            segments.append("Context from docs/context:\n" + "\n".join(doc_lines))
        else:
            segments.append("No documentation snippets matched the query, so only catalog data was used.")

        segments.append("This fallback summary is generated without the AI model because it was unavailable.")
        return "\n\n".join(segments)

    def _format_context_block(self, resources: Sequence, doc_chunks: Sequence[ContextChunk],
                              stats: Dict) -> str:
        lines: List[str] = []
        if resources:
            lines.append("RESOURCES:")
            for resource in resources:
                description = (getattr(resource, 'description', None) or '')[:180].strip()
                desc_text = description + ('…' if len(getattr(resource, 'description', None) or '') > 180 else '')
                lines.append(
                    f"- {getattr(resource, 'title', 'Unknown')} | {getattr(resource, 'category', None) or 'General'} | "
                    f"{getattr(resource, 'location', None) or 'Location TBD'} | "
                    f"Capacity: {getattr(resource, 'capacity', None) or 'varies'} | "
                    f"Restricted: {'yes' if getattr(resource, 'is_restricted', False) else 'no'} | "
                    f"{desc_text}"
                )
        else:
            lines.append("RESOURCES: No matching resources were found in the database.")

        if stats.get('most_requested'):
            lines.append("MOST REQUESTED:")
            for item in stats['most_requested']:
                lines.append(f"- {item['title']} ({item['total']} recent bookings)")

        if stats.get('category_counts'):
            counts_text = ', '.join(
                f"{entry['category']}: {entry['total']}"
                for entry in stats['category_counts']
            )
            lines.append(f"CATEGORY COUNTS: {counts_text}")

        if doc_chunks:
            lines.append("DOCUMENTATION:")
            for chunk in doc_chunks:
                lines.append(f"- {chunk.heading} ({chunk.source}): {chunk.preview}")
        else:
            lines.append("DOCUMENTATION: No snippets were relevant to this question.")

        return "\n".join(lines)

    # Statistical context ----------------------------------------------------

    def _build_insights(self) -> Dict:
        return {
            'most_requested': self._most_requested_resources(limit=3),
            'category_counts': ResourceDAL.category_distribution(limit=6),
            'total_resources': ResourceDAL.count_resources()
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

    # Tokenization + scoring --------------------------------------------------

    def _extract_keywords(self, text: str) -> List[str]:
        tokens = self._tokenize(text)
        keywords = [
            token for token in tokens
            if token not in self.STOP_WORDS and len(token) >= 2
        ]
        seen = set()
        ordered = []
        for token in keywords:
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
        text_parts = [
            getattr(resource, 'title', None),
            getattr(resource, 'description', None),
            getattr(resource, 'equipment', None),
            getattr(resource, 'location', None),
            getattr(resource, 'availability_rules', None)
        ]
        text = ' '.join(part for part in text_parts if part)
        heading = ' '.join(
            part for part in (getattr(resource, 'category', None), getattr(resource, 'location', None)) if part
        )
        return self._score_text(text, keywords, heading=heading)

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
