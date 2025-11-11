"""
Input validation utilities
Server-side validation for all user inputs
"""
import re
from datetime import datetime

class Validator:
    """Input validation utilities"""
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or len(email) > 254:
            return False
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_password(password):
        """Validate password strength (min 8 chars, 1 upper, 1 lower, 1 digit)"""
        if not password or len(password) < 8:
            return False, "Password must be at least 8 characters long"
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r'\d', password):
            return False, "Password must contain at least one digit"
        return True, "Valid"
    
    @staticmethod
    def validate_string(value, min_len=1, max_len=1000, field_name="Field"):
        """Validate string length"""
        if not value or not isinstance(value, str):
            return False, f"{field_name} is required"
        if len(value.strip()) < min_len:
            return False, f"{field_name} must be at least {min_len} characters"
        if len(value) > max_len:
            return False, f"{field_name} must not exceed {max_len} characters"
        return True, "Valid"
    
    @staticmethod
    def validate_integer(value, min_val=None, max_val=None, field_name="Field"):
        """Validate integer value"""
        try:
            val = int(value)
            if min_val is not None and val < min_val:
                return False, f"{field_name} must be at least {min_val}"
            if max_val is not None and val > max_val:
                return False, f"{field_name} must not exceed {max_val}"
            return True, val
        except (ValueError, TypeError):
            return False, f"{field_name} must be a valid number"
    
    @staticmethod
    def validate_datetime(datetime_str, field_name="Date/Time"):
        """Validate datetime string"""
        try:
            dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
            return True, dt
        except (ValueError, AttributeError):
            return False, f"{field_name} must be a valid date and time"
    
    @staticmethod
    def validate_rating(rating):
        """Validate rating (1-5)"""
        return Validator.validate_integer(rating, 1, 5, "Rating")
    
    @staticmethod
    def validate_role(role):
        """Validate user role"""
        valid_roles = ['student', 'staff', 'admin']
        if role not in valid_roles:
            return False, f"Role must be one of: {', '.join(valid_roles)}"
        return True, "Valid"
    
    @staticmethod
    def validate_status(status, valid_statuses):
        """Validate status against allowed values"""
        if status not in valid_statuses:
            return False, f"Status must be one of: {', '.join(valid_statuses)}"
        return True, "Valid"
    
    @staticmethod
    def sanitize_html(text):
        """Basic HTML sanitization"""
        if not text:
            return ""
        # Remove potentially dangerous tags
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'on\w+="[^"]*"',
            r"on\w+='[^']*'",
            r'javascript\s*:',
            r'vbscript\s*:',
        ]
        for pattern in dangerous_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text.strip()
