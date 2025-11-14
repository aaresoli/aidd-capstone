"""
Routes for the AI Resource Concierge experience.
"""
from flask import Blueprint, current_app, render_template, request

from src.data_access.resource_dal import ResourceDAL
from src.services.concierge_service import ConciergeService


concierge_bp = Blueprint('concierge', __name__, url_prefix='/concierge')


@concierge_bp.route('/', methods=['GET', 'POST'])
@concierge_bp.route('', methods=['GET', 'POST'])
def index():
    service = ConciergeService()
    doc_chunks = ConciergeService._load_context_chunks(service.context_root)
    doc_sources = sorted({chunk.source for chunk in doc_chunks})
    category_options = [row['category'] for row in ResourceDAL.category_distribution(limit=12)]

    question = ''
    selected_category = ''
    published_only = True
    concierge_result = None
    error_message = None

    if request.method == 'POST':
        question = (request.form.get('question') or '').strip()
        selected_category = (request.form.get('category') or '').strip()
        published_only = bool(request.form.get('published_only', '1'))

        if not question:
            error_message = 'Please enter a question before asking the concierge.'
        else:
            try:
                concierge_result = service.answer(
                    question,
                    category=selected_category or None,
                    published_only=published_only
                )
            except ValueError as exc:
                error_message = str(exc)
            except Exception as exc:  # pragma: no cover - defensive path
                current_app.logger.exception('Concierge request failed: %s', exc)
                error_message = 'Something went wrong while contacting the concierge. Please try again.'

    return render_template(
        'concierge/index.html',
        question=question,
        selected_category=selected_category,
        published_only=published_only,
        concierge_result=concierge_result,
        error_message=error_message,
        category_options=category_options,
        doc_sources=doc_sources
    )
