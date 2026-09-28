import base64
import json
from datetime import UTC, datetime, timedelta

import jwt
import pytest

from app.config import settings
from app.security import (
    ALGORITHM,
    MAX_PASSWORD_BYTES,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)

# --- passwords ---------------------------------------------------------------


def test_hash_is_not_the_password_and_verifies() -> None:
    hashed = hash_password("correct horse battery staple")

    assert "correct horse" not in hashed
    assert hashed.startswith("$2")  # bcrypt
    assert verify_password("correct horse battery staple", hashed)


def test_wrong_password_is_rejected() -> None:
    hashed = hash_password("correct horse battery staple")

    assert not verify_password("Correct horse battery staple", hashed)
    assert not verify_password("", hashed)


def test_same_password_gets_a_different_hash_each_time() -> None:
    assert hash_password("same-password-123") != hash_password("same-password-123")


def test_unicode_passwords_work() -> None:
    hashed = hash_password("pässwörd-日本語-🔐")

    assert verify_password("pässwörd-日本語-🔐", hashed)


def test_too_long_passwords_are_rejected_not_truncated() -> None:
    too_long = "a" * (MAX_PASSWORD_BYTES + 1)

    with pytest.raises(ValueError):
        hash_password(too_long)
    assert not verify_password(too_long, hash_password("a" * MAX_PASSWORD_BYTES))


def test_verifying_against_a_missing_user_hash_is_always_false() -> None:
    assert not verify_password("anything", None)
    assert not verify_password("", None)


# --- tokens ------------------------------------------------------------------


def test_token_round_trip() -> None:
    token = create_access_token("42")

    assert decode_access_token(token) == "42"


def test_token_carries_an_expiry() -> None:
    token = create_access_token("42", expires_minutes=5)

    payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
    remaining = payload["exp"] - datetime.now(UTC).timestamp()
    assert 0 < remaining <= 5 * 60


def test_expired_token_is_rejected() -> None:
    now = datetime.now(UTC)
    expired = jwt.encode(
        {"sub": "42", "iat": now - timedelta(hours=2), "exp": now - timedelta(hours=1)},
        settings.secret_key,
        algorithm=ALGORITHM,
    )

    assert decode_access_token(expired) is None


def test_token_signed_with_another_key_is_rejected() -> None:
    forged = jwt.encode(
        {"sub": "42", "exp": datetime.now(UTC) + timedelta(hours=1)},
        "another-secret-key-that-is-long-enough-123456",
        algorithm=ALGORITHM,
    )

    assert decode_access_token(forged) is None


def test_tampered_token_is_rejected() -> None:
    header, payload, signature = create_access_token("42").split(".")
    forged_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "1", "exp": 9999999999}).encode()
    ).rstrip(b"=")

    assert decode_access_token(f"{header}.{forged_payload.decode()}.{signature}") is None


def test_unsigned_alg_none_token_is_rejected() -> None:
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    unsigned = f"{b64({'alg': 'none', 'typ': 'JWT'})}.{b64({'sub': '42', 'exp': 9999999999})}."

    assert decode_access_token(unsigned) is None


def test_token_without_expiry_or_subject_is_rejected() -> None:
    no_exp = jwt.encode({"sub": "42"}, settings.secret_key, algorithm=ALGORITHM)
    no_sub = jwt.encode(
        {"exp": datetime.now(UTC) + timedelta(hours=1)}, settings.secret_key, algorithm=ALGORITHM
    )

    assert decode_access_token(no_exp) is None
    assert decode_access_token(no_sub) is None


def test_garbage_is_rejected() -> None:
    for garbage in ["", "abc", "a.b.c", "Bearer xyz"]:
        assert decode_access_token(garbage) is None
