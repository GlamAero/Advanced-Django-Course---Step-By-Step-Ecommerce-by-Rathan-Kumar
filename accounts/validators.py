from django.core.exceptions import ValidationError
import re

class CustomPasswordValidator:
    def validate(self, password, user=None):
        if len(password) < 12:
            raise ValidationError(
                "Password must be at least 12 characters long",
                code='password_too_short'
            )
        if not re.search(r'[A-Z]', password):
            raise ValidationError(
                "Password must contain at least one uppercase letter",
                code='password_no_upper'
            )
        if not re.search(r'[a-z]', password):
            raise ValidationError(
                "Password must contain at least one lowercase letter",
                code='password_no_lower'
            )
        if not re.search(r'[0-9]', password):
            raise ValidationError(
                "Password must contain at least one digit",
                code='password_no_digit'
            )
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValidationError(
                "Password must contain at least one special character",
                code='password_no_special'
            )

    def get_help_text(self):
        return (
            "Your password must contain at least 12 characters, including at least one uppercase letter, "
            "one lowercase letter, one digit, and one special character."
        )
