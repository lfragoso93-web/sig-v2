import re

PASSWORD_MIN_LENGTH = 10
PASSWORD_SPECIAL_CHARS = r"!@#$%^&*(),.?\":{}|<>"


def validate_strong_password(value: str) -> str:
    if len(value) < PASSWORD_MIN_LENGTH:
        raise ValueError(f"Senha deve ter no minimo {PASSWORD_MIN_LENGTH} caracteres")
    if not re.search(r"[A-Z]", value):
        raise ValueError("Senha deve conter pelo menos uma letra maiuscula")
    if not re.search(r"[a-z]", value):
        raise ValueError("Senha deve conter pelo menos uma letra minuscula")
    if not re.search(r"\d", value):
        raise ValueError("Senha deve conter pelo menos um numero")
    if not re.search(f"[{re.escape(PASSWORD_SPECIAL_CHARS)}]", value):
        raise ValueError(
            "Senha deve conter pelo menos um caractere especial "
            f"({PASSWORD_SPECIAL_CHARS})"
        )
    return value
