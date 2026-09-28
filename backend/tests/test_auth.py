from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.models import User
from app.security import ALGORITHM, create_access_token, verify_password
from app.services.users import MIN_PASSWORD_LENGTH, authenticate, create_user
from tests.conftest import TEST_USER_EMAIL, TEST_USER_PASSWORD


def login(client: TestClient, email: str = TEST_USER_EMAIL, password: str = TEST_USER_PASSWORD):
    # O endpoint segue o standard OAuth2: formulário com "username" (o email) e "password".
    return client.post("/auth/login", data={"username": email, "password": password})


# --- login --------------------------------------------------------------------


def test_login_returns_a_working_bearer_token(anonymous_client: TestClient, test_user: User):
    response = login(anonymous_client)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"

    me = anonymous_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == TEST_USER_EMAIL
    assert "hashed_password" not in me.json() and "password" not in me.json()


def test_login_is_case_insensitive_on_email(anonymous_client: TestClient, test_user: User):
    assert login(anonymous_client, email=TEST_USER_EMAIL.upper()).status_code == 200


def test_wrong_password_and_unknown_email_give_the_same_answer(
    anonymous_client: TestClient, test_user: User
):
    wrong_password = login(anonymous_client, password="not-the-right-password")
    unknown_email = login(anonymous_client, email="nobody@example.com")

    assert wrong_password.status_code == unknown_email.status_code == 401
    # Mensagens idênticas: não revelam que emails existem.
    assert wrong_password.json() == unknown_email.json()
    assert wrong_password.headers["www-authenticate"] == "Bearer"


def test_inactive_user_cannot_log_in(anonymous_client: TestClient, test_user: User, db: Session):
    test_user.is_active = False
    db.commit()

    assert login(anonymous_client).status_code == 401


def test_login_requires_both_fields(anonymous_client: TestClient):
    assert anonymous_client.post("/auth/login", data={"username": "a@b.c"}).status_code == 422
    assert anonymous_client.post("/auth/login", data={}).status_code == 422


# --- /auth/me and token handling ---------------------------------------------


def test_me_requires_a_token(anonymous_client: TestClient):
    response = anonymous_client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize("header", ["Bearer garbage", "Bearer ", "Basic abc", "abc"])
def test_me_rejects_malformed_authorization_headers(anonymous_client: TestClient, header: str):
    assert anonymous_client.get("/auth/me", headers={"Authorization": header}).status_code == 401


def test_me_rejects_expired_and_forged_tokens(anonymous_client: TestClient, test_user: User):
    now = datetime.now(UTC)
    expired = jwt.encode(
        {
            "sub": str(test_user.id),
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    forged = jwt.encode(
        {"sub": str(test_user.id), "exp": now + timedelta(hours=1)},
        "another-secret-key-that-is-long-enough-123456",
        algorithm=ALGORITHM,
    )

    for token in (expired, forged):
        response = anonymous_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 401


def test_valid_token_stops_working_if_the_user_is_deactivated_or_deleted(
    anonymous_client: TestClient, test_user: User, db: Session
):
    headers = {"Authorization": f"Bearer {create_access_token(str(test_user.id))}"}
    assert anonymous_client.get("/auth/me", headers=headers).status_code == 200

    test_user.is_active = False
    db.commit()
    assert anonymous_client.get("/auth/me", headers=headers).status_code == 401

    test_user.is_active = True
    db.commit()
    db.delete(test_user)
    db.commit()
    assert anonymous_client.get("/auth/me", headers=headers).status_code == 401


def test_token_with_a_non_numeric_subject_is_rejected(anonymous_client: TestClient):
    headers = {"Authorization": f"Bearer {create_access_token('not-a-number')}"}

    assert anonymous_client.get("/auth/me", headers=headers).status_code == 401


def test_openapi_advertises_the_bearer_scheme(anonymous_client: TestClient):
    schemes = anonymous_client.get("/openapi.json").json()["components"]["securitySchemes"]

    assert any(scheme["type"] == "oauth2" for scheme in schemes.values())


# --- user service ---------------------------------------------------------------


def test_create_user_normalises_email_and_stores_only_a_hash(db: Session):
    user = create_user(db, "  Ana.Silva@Example.COM ", " Ana Silva ", "a-long-enough-password")

    assert user.email == "ana.silva@example.com"
    assert user.full_name == "Ana Silva"
    assert user.hashed_password != "a-long-enough-password"
    assert verify_password("a-long-enough-password", user.hashed_password)


def test_create_user_rejects_weak_passwords_and_duplicates(db: Session):
    with pytest.raises(ValueError, match="at least"):
        create_user(db, "a@example.com", "A", "x" * (MIN_PASSWORD_LENGTH - 1))

    create_user(db, "a@example.com", "A", "a-long-enough-password")
    with pytest.raises(ValueError, match="already exists"):
        create_user(db, "A@EXAMPLE.COM", "A again", "another-long-password")


def test_authenticate(db: Session, test_user: User):
    assert authenticate(db, TEST_USER_EMAIL, TEST_USER_PASSWORD) is not None
    assert authenticate(db, TEST_USER_EMAIL, "wrong-password-value") is None
    assert authenticate(db, "nobody@example.com", TEST_USER_PASSWORD) is None
