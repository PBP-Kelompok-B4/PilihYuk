from django.core.exceptions import ValidationError

MESSAGE = "Password harus berisi huruf dan angka."


class LetterAndDigitValidator:
    def validate(self, password, user=None):
        if not (any(c.isalpha() for c in password) and any(c.isdigit() for c in password)):
            raise ValidationError(MESSAGE, code="password_needs_letter_and_digit")

    def get_help_text(self):
        return MESSAGE
