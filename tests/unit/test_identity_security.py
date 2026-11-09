from uuid import uuid4

from apps.shared.security.passwords import hash_password, verify_password
from apps.shared.security.tokens import create_access_token, parse_access_token


def test_passwords_are_hashed_with_argon2() -> None:
    password_hash = hash_password("correct-horse-battery-staple")
    assert password_hash != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", password_hash)
    assert not verify_password("wrong-password", password_hash)


def test_access_tokens_identify_the_issued_user() -> None:
    user_id = uuid4()
    assert parse_access_token(create_access_token(user_id)) == user_id
