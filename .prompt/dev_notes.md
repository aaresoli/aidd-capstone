# Development Notes - AI Interaction Log
## Campus Resource Hub

**Purpose:** This document logs all AI-assisted development interactions, outcomes, and learnings to help AI tools understand project context and development patterns.

**Last Updated:** 2024-11-15

---

## Table of Contents

- [Project Context](#project-context)
- [AI Interaction Log](#ai-interaction-log)
- [Key Learnings](#key-learnings)
- [Common Patterns](#common-patterns)
- [Architecture Decisions](#architecture-decisions)

---

## Project Context

### Technology Stack
- **Backend:** Flask 3.0.0 (Python 3.10+)
- **Database:** SQLite (development), PostgreSQL-ready
- **Frontend:** HTML5, CSS3, Bootstrap 5, Vanilla JavaScript
- **Authentication:** Flask-Login with bcrypt
- **AI Integration:** Local LLM (Ollama/LM Studio) for Resource Concierge

### Architecture Pattern
- **MVC (Model-View-Controller)** with strict separation of concerns
- **Data Access Layer (DAL)** for all database operations
- **Service Layer** for business logic (concierge, calendar, notifications)

### Key Directories
- `src/controllers/` - Flask route handlers (MVC Controllers)
- `src/models/` - Domain objects (MVC Models)
- `src/data_access/` - Database operations (DAL)
- `src/views/` - Jinja2 templates (MVC Views)
- `src/services/` - Business logic services
- `src/utils/` - Utility functions

### Important Conventions
- All database operations go through DAL modules (never direct SQL in controllers)
- Controllers validate input, check permissions, then delegate to DAL/services
- Models are data structures only (no persistence logic)
- Views use Jinja2 template inheritance from `layout.html`
- CSRF protection via Flask-WTF on all forms

---

## AI Interaction Log

### 2024-11-15 - Initial Setup
**Task:** Create `.prompt/` folder structure for AI-assisted development
**Outcome:** Created `dev_notes.md` and `golden_prompts.md` with structured templates
**Key Insight:** These files help AI tools understand project context, architecture patterns, and development history

### 2024-11-15 - AI Testing & Verification
**Task:** Implement comprehensive tests for AI feature verification
**Outcome:** Added 7 comprehensive tests in `tests/test_concierge.py` that verify:
- AI outputs only mention existing resources (no fabrication)
- AI outputs align with factual database data
- No fabricated information in responses
- Appropriate and non-biased responses
- Context retrieval uses actual database data
- Fallback responses use actual data
- All resource attributes are verifiable
**Key Insight:** AI components must be tested to ensure they never return fabricated or unverifiable results. All resource data in responses must match database records exactly.

---

## Key Learnings

### Database Operations
- Always use parameterized queries (prevents SQL injection)
- DAL methods return Model objects, not raw dictionaries
- Use transactions for multi-step operations
- Check for conflicts before creating bookings

### Authentication & Authorization
- Use `@login_required` decorator for protected routes
- Check `current_user.is_authenticated` before accessing user properties
- Role hierarchy: Admin > Staff > Student
- Account suspension checked in `before_request` hook

### Error Handling
- Use Flask's `flash()` for user-facing messages
- Log errors to console/file for debugging
- Return appropriate HTTP status codes
- Show user-friendly error pages (404, 500)

### Testing Patterns
- Use pytest fixtures in `conftest.py` for common setup
- Test DAL methods independently of controllers
- Integration tests cover full request/response cycles
- Mock external services (Google Calendar, LLM) in tests

---

## Common Patterns

### Creating a New Feature

1. **Model** (`src/models/models.py`)
   - Define data structure
   - Add validation methods if needed

2. **DAL** (`src/data_access/[feature]_dal.py`)
   - Create CRUD methods
   - Use parameterized queries
   - Return Model objects

3. **Controller** (`src/controllers/[feature]_controller.py`)
   - Register Flask blueprint
   - Add routes with `@login_required` where needed
   - Validate input, check permissions
   - Call DAL methods
   - Render templates or return JSON

4. **View** (`src/views/[feature]/`)
   - Create Jinja2 templates
   - Extend `layout.html`
   - Use Bootstrap 5 components
   - Include CSRF tokens in forms

5. **Tests** (`tests/test_[feature].py`)
   - Unit tests for DAL methods
   - Integration tests for controllers
   - Test permission checks

### Adding a New Database Table

1. Update `schema.sql` with CREATE TABLE statement
2. Add Model class in `src/models/models.py`
3. Create DAL module in `src/data_access/`
4. Update `src/data_access/__init__.py` to initialize table
5. Create migration SQL in `docs/migrations/`
6. Update ERD in `docs/ARCHITECTURE_DOCUMENTATION.md`

### Adding a New Service

1. Create service module in `src/services/`
2. Define service class with business logic methods
3. Import and use in controllers
4. Add tests in `tests/test_[service].py`
5. Document in `docs/ARCHITECTURE_DOCUMENTATION.md`

---

## Architecture Decisions

### Why MVC?
- Clear separation of concerns
- Easy to test each layer independently
- Scalable for team development
- Standard pattern for Flask applications

### Why DAL Layer?
- Centralizes database logic
- Makes database migration easier (SQLite → PostgreSQL)
- Prevents SQL injection (parameterized queries)
- Enables query optimization in one place

### Why Local LLM?
- Privacy: No data sent to external services
- Cost: No API fees
- Control: Full control over model and responses
- Compliance: Meets data privacy requirements

### Why SQLite for Development?
- Zero configuration
- File-based (easy to reset)
- Sufficient for development/testing
- Easy migration path to PostgreSQL

---

## Development Workflow

### Before Starting Work
1. Activate virtual environment
2. Ensure database is initialized
3. Review relevant documentation
4. Check existing tests for patterns

### During Development
1. Follow MVC pattern strictly
2. Write tests alongside code
3. Use meaningful variable names
4. Add comments for complex logic
5. Update documentation as needed

### After Completing Feature
1. Run tests: `pytest`
2. Check linter: `flake8` or `pylint`
3. Test manually in browser
4. Update `dev_notes.md` with learnings
5. Commit with descriptive message

---

## Known Issues & Solutions

### Issue: Database Locked
**Solution:** Ensure only one process accesses database at a time. Close database connections properly.

### Issue: CSRF Token Missing
**Solution:** Include `{{ csrf_token() }}` in all forms. Ensure Flask-WTF is configured.

### Issue: Import Errors
**Solution:** Ensure virtual environment is activated. Check `PYTHONPATH`. Verify `__init__.py` files exist.

### Issue: Template Not Found
**Solution:** Check template path matches blueprint registration. Ensure template extends `layout.html`.

---

## Future Enhancements

- [ ] Migrate to PostgreSQL for production
- [ ] Add Redis for session storage
- [ ] Implement API rate limiting
- [ ] Add comprehensive API documentation
- [ ] Set up CI/CD pipeline
- [ ] Add performance monitoring
- [ ] Implement caching layer

---

## Notes for AI Assistants

When working on this project:

1. **Always follow MVC pattern** - Controllers call DAL, DAL returns Models, Views render templates
2. **Check permissions** - Use `utils/permissions.py` helpers before allowing actions
3. **Validate input** - Use `utils/validators.py` for common validations
4. **Use existing patterns** - Look at similar features for consistency
5. **Update tests** - Add tests for new functionality
6. **Document changes** - Update relevant docs in `docs/` folder
7. **Respect architecture** - Don't bypass DAL or put business logic in views

**Common Mistakes to Avoid:**
- ❌ Direct SQL in controllers
- ❌ Business logic in views
- ❌ Skipping permission checks
- ❌ Hardcoding values that should be configurable
- ❌ Ignoring existing patterns

---

*This document should be updated after significant AI-assisted development sessions to maintain context for future interactions.*
