"""
Resource Controller
Handles resource CRUD operations and search
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import os
from datetime import datetime, timedelta
from collections import defaultdict
from urllib.parse import urlencode
from src.data_access.resource_dal import ResourceDAL
from src.data_access.review_dal import ReviewDAL
from src.data_access.booking_dal import BookingDAL
from src.utils.validators import Validator
from src.utils.permissions import user_has_role, can_manage_resource, is_admin, owns_resource
from src.data_access.admin_log_dal import AdminLogDAL
from src.utils.datetime_helpers import build_booking_calendar, utc_now_naive, parse_datetime

resource_bp = Blueprint('resource', __name__, url_prefix='/resources')
RESOURCE_CATEGORIES = ['Study Room', 'Lab Equipment', 'Event Space', 'AV Equipment', 'Tutoring', 'Other']
BROWSE_PAGE_SIZE = 9
BROWSE_SORT_OPTIONS = {
    'recent': 'Most Recent',
    'name_az': 'Name A–Z',
    'capacity_desc': 'Capacity (High to Low)',
    'capacity_asc': 'Capacity (Low to High)',
    'location_az': 'Location A–Z'
}

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def save_uploaded_images(files, existing_paths=None):
    """Persist uploaded images safely and return combined list of filenames"""
    saved_files = list(existing_paths) if existing_paths else []
    upload_dir = os.path.abspath(current_app.config['UPLOAD_FOLDER'])

    for file in files:
        if not file or not file.filename:
            continue

        if not allowed_file(file.filename):
            raise ValueError('Unsupported file type. Allowed types: ' + ', '.join(sorted(current_app.config['ALLOWED_EXTENSIONS'])))

        filename = secure_filename(file.filename)
        if not filename:
            raise ValueError('Invalid file name.')

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_name = f"{timestamp}_{filename}"
        target_path = os.path.abspath(os.path.join(upload_dir, safe_name))

        # Ensure the resolved path stays within the upload directory
        if not target_path.startswith(upload_dir + os.sep):
            raise ValueError('Invalid file path detected.')

        file.save(target_path)

        if safe_name not in saved_files:
            saved_files.append(safe_name)

    return saved_files

@resource_bp.route('/')
def list_resources():
    """List all published resources with enriched filters, sorting, and pagination."""
    args = request.args.to_dict(flat=True)
    keyword = args.get('keyword', '').strip()
    category = args.get('category', '').strip()
    location = args.get('location', '').strip()
    min_capacity_input = args.get('min_capacity', '').strip()
    available_from_input = args.get('available_from', '').strip()
    available_until_input = args.get('available_until', '').strip()
    sort = args.get('sort', 'recent')
    page_raw = args.get('page', '1')

    if sort not in BROWSE_SORT_OPTIONS:
        sort = 'recent'

    try:
        page = max(int(page_raw), 1)
    except ValueError:
        page = 1

    min_capacity = None
    if min_capacity_input:
        valid, result = Validator.validate_integer(min_capacity_input, 1, 10000, "Minimum capacity")
        if not valid:
            flash(result, 'danger')
        else:
            min_capacity = result

    available_start_dt = None
    available_end_dt = None
    if available_from_input or available_until_input:
        if not available_from_input or not available_until_input:
            flash('Please provide both availability start and end times.', 'warning')
        else:
            valid, parsed_start = Validator.validate_datetime(available_from_input, "Available from")
            if not valid:
                flash(parsed_start, 'danger')
            else:
                valid, parsed_end = Validator.validate_datetime(available_until_input, "Available until")
                if not valid:
                    flash(parsed_end, 'danger')
                elif parsed_end <= parsed_start:
                    flash('Availability end time must be after start time.', 'danger')
                else:
                    available_start_dt = parsed_start
                    available_end_dt = parsed_end

    resources, total_results = ResourceDAL.search_resources(
        keyword=keyword or None,
        category=category or None,
        location=location or None,
        min_capacity=min_capacity,
        available_start=available_start_dt.isoformat() if available_start_dt else None,
        available_end=available_end_dt.isoformat() if available_end_dt else None,
        sort=sort,
        page=page,
        per_page=BROWSE_PAGE_SIZE,
        include_total=True
    )

    total_pages = max((total_results + BROWSE_PAGE_SIZE - 1) // BROWSE_PAGE_SIZE, 1)
    if total_results and page > total_pages:
        page = total_pages
        resources, total_results = ResourceDAL.search_resources(
            keyword=keyword or None,
            category=category or None,
            location=location or None,
            min_capacity=min_capacity,
            available_start=available_start_dt.isoformat() if available_start_dt else None,
            available_end=available_end_dt.isoformat() if available_end_dt else None,
            sort=sort,
            page=page,
            per_page=BROWSE_PAGE_SIZE,
            include_total=True
        )
        total_pages = max((total_results + BROWSE_PAGE_SIZE - 1) // BROWSE_PAGE_SIZE, 1)

    resource_ids = [resource.resource_id for resource in resources]
    upcoming_bookings = BookingDAL.get_bookings_for_resources(resource_ids, statuses=['pending', 'approved'])
    bookings_by_resource = defaultdict(list)
    for booking in upcoming_bookings:
        start_dt = parse_datetime(booking.start_datetime)
        end_dt = parse_datetime(booking.end_datetime)
        if not start_dt or not end_dt:
            continue
        bookings_by_resource[booking.resource_id].append((start_dt, end_dt))

    for resource_id, intervals in bookings_by_resource.items():
        intervals.sort(key=lambda pair: pair[0])

    now = utc_now_naive()

    def next_available_window(intervals):
        """Return a tuple describing the next free window (start, end) if determinable."""
        if not intervals:
            return now, None
        window_start = now
        for start_dt, end_dt in intervals:
            if end_dt <= window_start:
                continue
            if start_dt <= window_start < end_dt:
                window_start = end_dt
                continue
            if window_start < start_dt:
                return window_start, start_dt
        return window_start, None

    def format_window(window):
        start_dt, end_dt = window
        if not start_dt:
            return None
        day_label = 'Today'
        if start_dt.date() == (now + timedelta(days=1)).date():
            day_label = 'Tomorrow'
        elif start_dt.date() != now.date():
            day_label = start_dt.strftime('%b %d')
        start_label = start_dt.strftime('%I:%M %p').lstrip('0')
        if end_dt:
            end_label = end_dt.strftime('%I:%M %p').lstrip('0')
            return f"{day_label}, {start_label} – {end_label}"
        return f"{day_label}, {start_label} onward"
    
    def summarize_availability(window):
        start_dt, _ = window
        if not start_dt:
            return None, None
        delta = start_dt - now
        if delta <= timedelta(minutes=5):
            return 'Open now', 'success'
        if delta <= timedelta(hours=24):
            return 'Available soon', 'info'
        return 'Limited availability', 'warning'

    def can_access_resource(resource):
        """Students can view unrestricted resources; staff/admin can view all."""
        if not getattr(resource, 'is_restricted', False):
            return True
        if not current_user.is_authenticated:
            return False
        return user_has_role('staff', 'admin') or resource.owner_id == current_user.user_id

    resources_with_context = []
    top_rated_threshold = 4.5
    for resource in resources:
        intervals = bookings_by_resource.get(resource.resource_id, [])
        window = next_available_window(intervals) if intervals else (now, None)
        label = format_window(window)
        availability_status, availability_badge = summarize_availability(window)
        stats = ReviewDAL.get_resource_rating_stats(resource.resource_id)
        avg_rating = stats['avg_rating'] if stats and stats['avg_rating'] else 0
        total_reviews = stats['total_reviews'] if stats else 0
        resources_with_context.append({
            'resource': resource,
            'avg_rating': round(avg_rating, 1),
            'total_reviews': total_reviews,
            'is_top_rated': avg_rating >= top_rated_threshold and total_reviews >= 3,
            'can_access': can_access_resource(resource),
            'restriction_note': getattr(resource, 'restriction_note', None),
            'next_available': label,
            'availability_status': availability_status,
            'availability_badge': availability_badge
        })

    def build_query_url(overrides=None, removals=None, preserve_page=False):
        params = {k: v for k, v in args.items() if v}
        overrides = overrides or {}
        removals = removals or []
        for key in removals:
            params.pop(key, None)
        if not preserve_page:
            params.pop('page', None)
        for key, value in overrides.items():
            if value in [None, '']:
                params.pop(key, None)
            else:
                params[key] = value
        query = urlencode(params)
        base_url = url_for('resource.list_resources')
        return f"{base_url}?{query}" if query else base_url

    applied_filters = []
    if keyword:
        applied_filters.append({
            'label': f"Keyword: {keyword}",
            'remove_url': build_query_url(removals=['keyword'])
        })
    if category:
        applied_filters.append({
            'label': category,
            'remove_url': build_query_url(removals=['category'])
        })
    if location:
        applied_filters.append({
            'label': f"Location: {location}",
            'remove_url': build_query_url(removals=['location'])
        })
    if min_capacity is not None:
        applied_filters.append({
            'label': f"Min capacity: {min_capacity}",
            'remove_url': build_query_url(removals=['min_capacity'])
        })
    if available_start_dt and available_end_dt:
        range_label = (
            f"{available_start_dt.strftime('%b %d %I:%M %p')} → "
            f"{available_end_dt.strftime('%b %d %I:%M %p')}"
        )
        applied_filters.append({
            'label': f"Available: {range_label}",
            'remove_url': build_query_url(removals=['available_from', 'available_until'])
        })

    summary_fragments = []
    if keyword:
        summary_fragments.append(f"for '{keyword}'")
    if category:
        summary_fragments.append(f"in '{category}'")
    if location:
        summary_fragments.append(f"near '{location}'")
    if min_capacity is not None:
        summary_fragments.append(f"with capacity ≥ {min_capacity}")
    if available_start_dt and available_end_dt:
        summary_fragments.append(
            f"between {available_start_dt.strftime('%b %d, %I:%M %p')} "
            f"and {available_end_dt.strftime('%b %d, %I:%M %p')}"
        )
    filter_summary = f"Showing {total_results} resources"
    if summary_fragments:
        filter_summary = f"Showing {total_results} resources {' '.join(summary_fragments)}."

    pagination = {
        'current': page,
        'total_pages': total_pages,
        'has_prev': page > 1,
        'has_next': page < total_pages,
        'prev_url': build_query_url(overrides={'page': page - 1}, preserve_page=True) if page > 1 else None,
        'next_url': build_query_url(overrides={'page': page + 1}, preserve_page=True) if page < total_pages else None,
        'pages': []
    }
    for number in range(1, total_pages + 1):
        pagination['pages'].append({
            'number': number,
            'url': build_query_url(overrides={'page': number}, preserve_page=True),
            'is_active': number == page
        })

    return render_template(
        'resources/list.html',
        resources=resources_with_context,
        categories=RESOURCE_CATEGORIES,
        selected_keyword=keyword,
        selected_category=category,
        selected_location=location,
        selected_min_capacity=min_capacity_input,
        selected_sort=sort,
        selected_available_from=available_from_input,
        selected_available_until=available_until_input,
        sort_options=BROWSE_SORT_OPTIONS,
        total_results=total_results,
        filter_summary=filter_summary,
        applied_filters=applied_filters,
        pagination=pagination
    )

@resource_bp.route('/<int:resource_id>')
def detail(resource_id):
    """Resource detail page"""
    resource, avg_rating, review_count = ResourceDAL.get_resource_with_avg_rating(resource_id)
    
    if not resource or resource.status != 'published':
        flash('Resource not found', 'danger')
        return redirect(url_for('resource.list_resources'))
    
    reviews = ReviewDAL.get_reviews_by_resource(resource_id)
    stats = ReviewDAL.get_resource_rating_stats(resource_id)
    
    # Check if current user has reviewed
    has_reviewed = False
    if current_user.is_authenticated:
        has_reviewed = ReviewDAL.user_has_reviewed(resource_id, current_user.user_id)
    
    return render_template('resources/detail.html',
                         resource=resource,
                         avg_rating=avg_rating,
                         review_count=review_count,
                         reviews=reviews,
                         stats=stats,
                         has_reviewed=has_reviewed)

@resource_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create a new resource"""
    categories = RESOURCE_CATEGORIES

    if not user_has_role('staff', 'admin'):
        flash('Only staff and administrators can add resources.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        capacity = request.form.get('capacity', '').strip()
        equipment = request.form.get('equipment', '').strip()
        availability_rules = request.form.get('availability_rules', '').strip()
        is_restricted = request.form.get('is_restricted') == 'on'
        status = request.form.get('status', 'draft')

        if category not in categories:
            flash('Please choose a valid category.', 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)
        
        # Validation
        valid, msg = Validator.validate_string(title, 3, 200, "Title")
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)

        valid, msg = Validator.validate_string(location, 2, 255, "Location")
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)
        
        valid, msg = Validator.validate_string(description, 10, 5000, "Description")
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)
        
        # Sanitize inputs
        title = Validator.sanitize_html(title)
        location = Validator.sanitize_html(location)
        description = Validator.sanitize_html(description)
        availability_rules = Validator.sanitize_html(availability_rules) if availability_rules else None
        
        # Validate capacity if provided
        capacity_val = None
        if capacity:
            valid, capacity_val = Validator.validate_integer(capacity, 1, 1000, "Capacity")
            if not valid:
                flash(capacity_val, 'danger')
                return render_template('resources/create.html', categories=categories, form_data=request.form)

        valid, msg = Validator.validate_status(status, ['draft', 'published'])
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)

        equipment_list = None
        if equipment:
            tokens = []
            for line in equipment.replace('\r', '').split('\n'):
                for token in line.split(','):
                    cleaned = token.strip()
                    if cleaned:
                        tokens.append(cleaned)
            equipment_list = ', '.join(tokens) if tokens else None
        
        # Handle file upload
        image_paths = []
        if 'images' in request.files:
            files = request.files.getlist('images')
            try:
                image_paths = save_uploaded_images(files)
            except ValueError as upload_error:
                flash(str(upload_error), 'danger')
                return render_template('resources/create.html', categories=categories, form_data=request.form)
        
        images_str = ','.join(image_paths) if image_paths else None
        
        try:
            resource = ResourceDAL.create_resource(
                owner_id=current_user.user_id,
                title=title,
                description=description,
                category=category,
                location=location,
                capacity=capacity_val,
                images=images_str,
                equipment=equipment_list,
                availability_rules=availability_rules,
                is_restricted=is_restricted,
                status=status
            )
            flash('Resource created successfully!', 'success')
            return redirect(url_for('resource.detail', resource_id=resource.resource_id))
        except Exception as e:
            flash(f'Error creating resource: {str(e)}', 'danger')
            return render_template('resources/create.html', categories=categories, form_data=request.form)
    
    return render_template('resources/create.html', categories=categories, form_data={})

@resource_bp.route('/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(resource_id):
    """Edit a resource"""
    resource = ResourceDAL.get_resource_by_id(resource_id)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if not can_manage_resource(resource):
        flash('You do not have permission to edit this resource', 'danger')
        return redirect(url_for('resource.detail', resource_id=resource_id))
    
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        category = request.form.get('category', '').strip()
        location = request.form.get('location', '').strip()
        capacity = request.form.get('capacity', '').strip()
        equipment = request.form.get('equipment', '').strip()
        availability_rules = request.form.get('availability_rules', '').strip()
        is_restricted = request.form.get('is_restricted') == 'on'
        status = request.form.get('status', 'draft')

        if category not in RESOURCE_CATEGORIES:
            flash('Please choose a valid category.', 'danger')
            return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)
        
        # Validation (same as create)
        valid, msg = Validator.validate_string(title, 3, 200, "Title")
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)

        valid, msg = Validator.validate_string(location, 2, 255, "Location")
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)
        
        title = Validator.sanitize_html(title)
        location = Validator.sanitize_html(location)
        description = Validator.sanitize_html(description)
        availability_rules = Validator.sanitize_html(availability_rules) if availability_rules else None
        
        capacity_val = None
        if capacity:
            valid, capacity_val = Validator.validate_integer(capacity, 1, 1000, "Capacity")
            if not valid:
                flash(capacity_val, 'danger')
                return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)

        valid, msg = Validator.validate_status(status, ['draft', 'published', 'archived'])
        if not valid:
            flash(msg, 'danger')
            return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)

        equipment_list = None
        if equipment:
            tokens = []
            for line in equipment.replace('\r', '').split('\n'):
                for token in line.split(','):
                    cleaned = token.strip()
                    if cleaned:
                        tokens.append(cleaned)
            equipment_list = ', '.join(tokens) if tokens else None
        
        # Handle new file uploads
        image_paths = resource.images.split(',') if resource.images else []
        if 'images' in request.files:
            files = request.files.getlist('images')
            try:
                image_paths = save_uploaded_images(files, existing_paths=image_paths)
            except ValueError as upload_error:
                flash(str(upload_error), 'danger')
                return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data=request.form)
        
        images_str = ','.join(image_paths) if image_paths else None
        
        admin_override = is_admin() and not owns_resource(resource)
        try:
            ResourceDAL.update_resource(
                resource_id=resource_id,
                title=title,
                description=description,
                category=category,
                location=location,
                capacity=capacity_val,
                images=images_str,
                equipment=equipment_list,
                availability_rules=availability_rules,
                is_restricted=is_restricted,
                status=status
            )
            flash('Resource updated successfully!', 'success')
            if admin_override:
                AdminLogDAL.record(
                    current_user.user_id,
                    'resource_update_override',
                    'resources',
                    f'resource_id={resource_id};owner_id={resource.owner_id}'
                )
            return redirect(url_for('resource.detail', resource_id=resource_id))
        except Exception as e:
            flash(f'Error updating resource: {str(e)}', 'danger')
    
    return render_template('resources/edit.html', resource=resource, categories=RESOURCE_CATEGORIES, form_data={})
    
    categories = ['Study Room', 'Lab Equipment', 'Event Space', 'AV Equipment', 'Tutoring', 'Other']
    return render_template('resources/edit.html', resource=resource, categories=categories)

@resource_bp.route('/<int:resource_id>/delete', methods=['POST'])
@login_required
def delete(resource_id):
    """Delete a resource"""
    resource = ResourceDAL.get_resource_by_id(resource_id)
    
    if not resource:
        flash('Resource not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if not can_manage_resource(resource):
        flash('You do not have permission to delete this resource', 'danger')
        return redirect(url_for('resource.detail', resource_id=resource_id))
    
    try:
        ResourceDAL.delete_resource(resource_id)
        flash('Resource deleted successfully', 'success')
        if is_admin() and not owns_resource(resource):
            AdminLogDAL.record(
                current_user.user_id,
                'resource_delete_override',
                'resources',
                f'resource_id={resource_id};owner_id={resource.owner_id}'
            )
    except Exception as e:
        flash(f'Error deleting resource: {str(e)}', 'danger')
    
    return redirect(url_for('dashboard'))
