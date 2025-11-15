# Golden Prompts - High-Impact AI Interactions
## Campus Resource Hub

**Purpose:** This document captures the most effective prompts and their outcomes to help AI tools generate accurate, contextually relevant code for this project.

**Last Updated:** 2024-11-15

---

## Table of Contents

- [Architecture & Structure](#architecture--structure)
- [Database & Data Access](#database--data-access)
- [Controllers & Routes](#controllers--routes)
- [Frontend & Views](#frontend--views)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Feature Development](#feature-development)

---

## Architecture & Structure

### Prompt: Understanding MVC Pattern
```
Explain how the MVC pattern is implemented in this Campus Resource Hub project. 
Show me the flow from a user request through the controller, to the DAL, and back to the view.
Include examples from the booking flow.
```

**Why it works:** Helps AI understand the strict separation of concerns and how data flows through the application.

**Key Context:**
- Controllers handle HTTP requests/responses
- DAL handles all database operations
- Models are data structures only
- Views render HTML templates

---

### Prompt: Adding a New Feature Following MVC
```
I need to add a new feature for [feature_name]. 
Following the MVC pattern used in this project:
1. What Model class should I create?
2. What DAL methods are needed?
3. What controller routes should I add?
4. What view templates should I create?
5. What tests should I write?

Reference the existing [similar_feature] implementation for patterns.
```

**Why it works:** Ensures new features follow established patterns and maintain consistency.

**Example Outcome:** When adding waitlist feature, this prompt generated:
- `WaitlistEntry` model
- `waitlist_dal.py` with `add_to_waitlist()`, `get_waitlist_entries()`
- `booking_controller.py` routes for waitlist management
- `bookings/waitlist.html` template
- `test_waitlist.py` with comprehensive tests

---

## Database & Data Access

### Prompt: Creating a DAL Method
```
Create a DAL method in [module]_dal.py following the existing patterns:
- Method name: [method_name]
- Purpose: [description]
- Parameters: [list]
- Returns: [Model object or list]
- Should handle: [edge cases]

Look at [similar_method] in [similar_dal].py for the pattern.
Use parameterized queries to prevent SQL injection.
```

**Why it works:** Ensures database operations follow security best practices and existing patterns.

**Key Pattern:**
```python
def get_resource_by_id(resource_id):
    """Get resource by ID. Returns Resource model or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM resources WHERE resource_id = ?",
        (resource_id,)
    )
    row = cursor.fetchone()
    conn.close()
    return Resource.from_dict(row) if row else None
```

---

### Prompt: Database Migration
```
I need to add a new column [column_name] of type [type] to the [table_name] table.
Create a migration SQL file following the pattern in docs/migrations/.
Include:
1. ALTER TABLE statement
2. Default value handling
3. Index creation if needed
4. Rollback instructions
```

**Why it works:** Ensures migrations are safe, reversible, and documented.

---

## Controllers & Routes

### Prompt: Creating a Protected Route
```
Create a Flask route in [controller].py for [route_path] that:
- Requires login (@login_required)
- Checks [permission] using utils/permissions.py
- Validates input using utils/validators.py
- Calls [dal_method] from [dal_module]
- Renders [template] or redirects with flash message

Follow the pattern from [similar_route] in the same controller.
```

**Why it works:** Ensures routes follow security and architecture patterns.

**Example Pattern:**
```python
@resource_bp.route('/resources/<int:resource_id>/edit', methods=['GET', 'POST'])
@login_required
def edit(resource_id):
    resource = ResourceDAL.get_resource_by_id(resource_id)
    
    if not can_manage_resource(resource):
        flash('Access denied', 'danger')
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # Validate and update
        pass
    
    return render_template('resources/edit.html', resource=resource)
```

---

### Prompt: Handling Form Submission
```
Create a POST route handler that:
1. Validates CSRF token (automatic with Flask-WTF)
2. Validates form data using [validator_function]
3. Checks user permissions
4. Calls DAL method to persist data
5. Sends notification if needed
6. Redirects with appropriate flash message

Handle errors gracefully and show user-friendly messages.
```

**Why it works:** Ensures form handling is secure and user-friendly.

---

## Frontend & Views

### Prompt: Creating a Template
```
Create a Jinja2 template at [path] that:
- Extends layout.html
- Uses Bootstrap 5 components
- Includes CSRF token in forms
- Shows flash messages
- Displays [data] from controller
- Follows the pattern from [similar_template]

Include proper error handling and loading states.
```

**Why it works:** Ensures templates are consistent, secure, and accessible.

**Key Template Pattern:**
```jinja2
{% extends "layout.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
<div class="container">
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="alert alert-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    
    <!-- Content here -->
</div>
{% endblock %}
```

---

### Prompt: Adding JavaScript Functionality
```
Add JavaScript to [template] that:
- Handles [interaction]
- Makes AJAX call to [endpoint]
- Updates [element] with response
- Shows loading state during request
- Handles errors gracefully

Follow the pattern from [similar_js_file] in src/static/js/.
```

**Why it works:** Ensures JavaScript follows existing patterns and error handling.

---

## Testing

### Prompt: Writing Comprehensive Tests
```
Write pytest tests for [feature] that cover:
1. Happy path scenarios
2. Permission checks (unauthorized access)
3. Input validation (invalid data)
4. Edge cases ([specific cases])
5. Error handling

Use fixtures from conftest.py. Follow patterns from test_[similar_feature].py.
```

**Why it works:** Ensures comprehensive test coverage following project patterns.

**Test Pattern:**
```python
def test_create_booking_success(client, auth_student, sample_resource):
    """Test successful booking creation."""
    response = client.post('/bookings/create', data={
        'resource_id': sample_resource.resource_id,
        'start_datetime': '2024-11-20T10:00:00',
        'end_datetime': '2024-11-20T12:00:00',
        'csrf_token': get_csrf_token(client)
    })
    assert response.status_code == 302
    assert b'Booking request submitted' in response.data

def test_create_booking_unauthorized(client, sample_resource):
    """Test booking creation without login."""
    response = client.post('/bookings/create', data={...})
    assert response.status_code == 302
    assert '/auth/login' in response.location
```

---

## Troubleshooting

### Prompt: Debugging Database Issues
```
I'm getting [error] when [action]. 
The relevant code is in [file] at [location].
Check:
1. Database connection handling
2. SQL query syntax
3. Parameter binding
4. Transaction management
5. Error handling

Compare with working code in [similar_file].
```

**Why it works:** Helps identify common database operation mistakes.

---

### Prompt: Fixing Permission Errors
```
Users are getting "Access denied" when they should have access.
The route is [route] in [controller].
Check:
1. Permission check logic
2. Role assignments
3. Ownership checks
4. Before_request hooks

Review utils/permissions.py and similar routes.
```

**Why it works:** Helps identify authorization logic issues.

---

## Feature Development

### Prompt: Implementing Booking Approval Flow
```
Implement the booking approval flow where:
1. Staff can approve/deny bookings for their resources
2. Admin can approve/deny any booking
3. Notifications are sent to requester
4. Booking status is updated in database
5. Admin log entry is created

Follow existing patterns in booking_controller.py and notification_center.py.
```

**Why it works:** Breaks down complex features into clear steps following existing patterns.

**Outcome:** Generated complete approval workflow with proper permission checks, notifications, and audit logging.

---

### Prompt: Adding Search Functionality
```
Add search functionality to [feature] that:
- Filters by [criteria]
- Supports keyword search
- Sorts by [options]
- Paginates results
- Shows result count

Follow the pattern from resource_controller.py search route.
Use DAL methods for database queries, not raw SQL in controller.
```

**Why it works:** Ensures search follows existing patterns and security practices.

---

## Best Practices for Prompting

### ✅ DO:
- Reference existing code patterns
- Specify the architecture pattern to follow
- Mention security considerations
- Ask for tests to be included
- Request documentation updates

### ❌ DON'T:
- Ask to bypass DAL layer
- Request business logic in views
- Skip permission checks
- Ignore existing patterns
- Forget error handling

---

## Prompt Templates

### For New Features
```
Add [feature] following MVC pattern:
- Model: [description]
- DAL: [methods needed]
- Controller: [routes needed]
- View: [templates needed]
- Tests: [coverage needed]

Reference [similar_feature] for patterns.
```

### For Bug Fixes
```
Fix [issue] in [file]:
- Problem: [description]
- Expected: [behavior]
- Current: [behavior]
- Location: [file:line]

Check similar code in [reference_file] for correct pattern.
```

### For Refactoring
```
Refactor [code] to:
- [improvement]
- Follow [pattern]
- Improve [aspect]

Maintain backward compatibility and update tests.
```

---

## High-Impact Outcomes

### 1. Complete Booking System
**Prompt:** "Implement the full booking system with conflict detection, approval workflow, and notifications following MVC pattern."

**Outcome:** Generated complete booking flow with:
- BookingDAL with conflict checking
- BookingController with approval routes
- Booking templates with calendar integration
- Comprehensive tests

### 2. AI Concierge Service
**Prompt:** "Create an AI concierge service that uses local LLM to answer questions about campus resources, combining database queries with context documents."

**Outcome:** Generated:
- ConciergeService with RAG pipeline
- LocalLLMClient abstraction
- Context retrieval system
- Integration with resource database

### 3. Calendar Integration
**Prompt:** "Implement Google Calendar OAuth integration with event sync, following Flask OAuth patterns and storing credentials securely."

**Outcome:** Generated:
- OAuth 2.0 flow implementation
- CalendarService for event management
- Secure credential storage
- iCal export functionality

---

*Update this document when you discover prompts that consistently produce high-quality, contextually appropriate code for this project.*
