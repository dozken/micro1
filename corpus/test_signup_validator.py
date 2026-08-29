from signup_validator import (
    validate_email,
    validate_password,
    validate_signup,
    validate_username,
)


def test_username_too_short():
    r = validate_username("ab")
    assert not r.is_valid
    assert any("at least" in e for e in r.errors)


def test_username_min_length_boundary_ok():
    r = validate_username("abc")
    assert r.is_valid


def test_username_too_long():
    r = validate_username("a" * 21)
    assert not r.is_valid


def test_username_max_length_boundary_ok():
    r = validate_username("a" * 20)
    assert r.is_valid


def test_username_rejects_special_chars():
    r = validate_username("bad-name!")
    assert not r.is_valid


def test_username_allows_underscore_and_digits():
    r = validate_username("user_123")
    assert r.is_valid


def test_username_cannot_start_with_digit():
    r = validate_username("1abc")
    assert not r.is_valid


def test_email_valid():
    assert validate_email("a@b.com").is_valid
    assert validate_email("first.last+tag@sub.example.co").is_valid


def test_email_invalid():
    assert not validate_email("not-an-email").is_valid
    assert not validate_email("missing@tld").is_valid
    assert not validate_email("@missinguser.com").is_valid


def test_password_too_short():
    r = validate_password("Ab1defg")  # 7 chars
    assert not r.is_valid


def test_password_min_length_boundary_ok():
    r = validate_password("Ab1defgh")  # exactly 8 chars
    assert r.is_valid


def test_password_requires_upper_lower_digit():
    assert not validate_password("alllowercase1").is_valid
    assert not validate_password("ALLUPPERCASE1").is_valid
    assert not validate_password("NoDigitsHere").is_valid


def test_password_rejects_containing_username():
    r = validate_password("Alice1234", username="alice")
    assert not r.is_valid
    assert any("username" in e for e in r.errors)


def test_password_username_case_insensitive_match():
    r = validate_password("MyAliceIsHere1", username="ALICE")
    assert not r.is_valid


def test_validate_signup_aggregates_all_errors():
    r = validate_signup("1bad", "not-an-email", "short")
    assert not r.is_valid
    assert len(r.errors) >= 3


def test_validate_signup_happy_path():
    r = validate_signup("carol_99", "carol@example.com", "Str0ngPass")
    assert r.is_valid
