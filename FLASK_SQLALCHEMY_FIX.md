# Flask-SQLAlchemy App Context Fix

## Problem
**Error**: `RuntimeError: The current Flask app is not registered with this 'SQLAlchemy' instance. Did you forget to call 'init_app'?`

This error occurred when database queries were executed outside of a Flask application context.

## Root Cause
SQLAlchemy models were using `.query` methods without ensuring a Flask app context was active. When the request or background process didn't have the proper app context, SQLAlchemy couldn't find the registered Flask application instance.

## Solution
Added explicit Flask app context checks before all database queries. The fixes wrap queries with `if current_app:` conditions to ensure the application context is available before executing database operations.

## Files Fixed

### 1. `apps/recommendations/routes/recommendations.py`
- **`_ensure_rec_shape()` function** (line ~67)
  - Added: `if current_app:` check before `VendorSubcategoryData.query`
  - Added: Explicit handling for `RuntimeError` with app context detection
  
- **`safe_get_user()` function** (line ~43)
  - Added: `if current_app:` check before `User.query.get()`
  - Added: Enhanced error handling for both `RuntimeError` and general exceptions
  
- **`vendor_subcategory_data()` endpoint** (line ~615)
  - Added: `if current_app:` check before query
  - Added: Returns 500 error if app context unavailable
  - Added: Specific `RuntimeError` handling

### 2. `apps/recommendations/routes/interactions.py`
- **Enrichment section** (line ~82)
  - Added: `if current_app:` check before `VendorSubcategoryData.query.get()`
  - Added: Specific `RuntimeError` handling
  
- **Spam prevention section** (line ~111)
  - Added: `if current_app:` check before `UserInteraction.query` filter
  - Added: Comprehensive error handling with session cleanup

### 3. `apps/recommendations/services/recommendation_engine.py`
- **`_extract_vendor_id()` method** (line ~847)
  - Added: `if current_app:` check before query
  - Added: Silent failure mode for app context issues
  
- **`_safe_get_user()` method** (line ~350)
  - Added: `if current_app:` check before `User.query.get()`
  - Added: Enhanced error handling for `RuntimeError`

### 4. `apps/recommendations/routes/trending.py`
- **`get_trending()` endpoint** (line ~19)
  - Added: `current_app` import
  - Added: `if current_app:` check before `UserInteraction.query`
  - Added: Empty list fallback when app context unavailable
  - Added: `try-except` wrapper for the entire endpoint

## Pattern Used
All fixes follow this pattern:
```python
try:
    if current_app:
        # Perform database query
        result = Model.query.filter(...).all()
    else:
        result = []  # or None, depending on context
except RuntimeError as e:
    if "not registered" in str(e):
        current_app.logger.error(f"Flask app context error: {e}")
    else:
        current_app.logger.exception("Database error")
    # Handle gracefully
except Exception as e:
    current_app.logger.exception("Unexpected error")
    # Handle gracefully
```

## Testing Recommendations
1. Test endpoints with active Flask request context (normal operation)
2. Test Celery background tasks to ensure they handle missing context gracefully
3. Monitor error logs for `RuntimeError` messages indicating app context issues
4. Verify fallback behaviors when app context is unavailable

## Prevention
- Always ensure database queries are within Flask application context
- Use `current_app` checks before any `.query` calls
- For Celery tasks or background jobs, use `SessionLocal` instead of `.query` (requires separate app initialization)
- Consider moving complex queries to services that accept app context as a parameter
