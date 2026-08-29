"""Validation rules for a signup form: username, email, password."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")

USERNAME_MIN_LEN = 3
USERNAME_MAX_LEN = 20
PASSWORD_MIN_LEN = 8


@dataclass
class ValidationResult:
    errors: List[str] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        return len(self.errors) == 0


def validate_username(username: str) -> ValidationResult:
    result = ValidationResult()
    if len(username) < USERNAME_MIN_LEN:
        result.errors.append(f"username must be at least {USERNAME_MIN_LEN} characters")
    if len(username) > USERNAME_MAX_LEN:
        result.errors.append(f"username must be at most {USERNAME_MAX_LEN} characters")
    if not _USERNAME_RE.match(username):
        result.errors.append("username may only contain letters, digits, and underscores")
    if username[:1].isdigit():
        result.errors.append("username may not start with a digit")
    return result


def validate_email(email: str) -> ValidationResult:
    result = ValidationResult()
    if not _EMAIL_RE.match(email):
        result.errors.append("email is not a valid address")
    return result


def validate_password(password: str, username: str = "") -> ValidationResult:
    result = ValidationResult()
    if len(password) < PASSWORD_MIN_LEN:
        result.errors.append(f"password must be at least {PASSWORD_MIN_LEN} characters")
    if not any(c.isupper() for c in password):
        result.errors.append("password must contain an uppercase letter")
    if not any(c.islower() for c in password):
        result.errors.append("password must contain a lowercase letter")
    if not any(c.isdigit() for c in password):
        result.errors.append("password must contain a digit")
    if username and username.lower() in password.lower():
        result.errors.append("password must not contain the username")
    return result


def validate_signup(username: str, email: str, password: str) -> ValidationResult:
    result = ValidationResult()
    for sub in (
        validate_username(username),
        validate_email(email),
        validate_password(password, username),
    ):
        result.errors.extend(sub.errors)
    return result
