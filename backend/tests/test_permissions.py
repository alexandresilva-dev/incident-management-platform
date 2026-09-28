"""O que um analista pode e não pode fazer, e a gestão de utilizadores por admins."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import User
from app.models.enums import UserRole
from tests.conftest import ANALYST_EMAIL

STRONG_PASSWORD = "a-long-enough-password"


def create_user(client: TestClient, **overrides):
    payload = {
        "email": "new.user@example.com",
        "full_name": "New User",
        "password": STRONG_PASSWORD,
        **overrides,
    }
    return client.post("/users", json=payload)


# --- o que só os admins podem fazer -------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/users"),
        ("POST", "/users"),
        ("PATCH", "/users/1"),
        ("DELETE", "/assets/1"),
        ("DELETE", "/vulnerabilities/1"),
    ],
)
def test_analysts_are_forbidden_from_admin_operations(
    analyst_client: TestClient, method: str, path: str
) -> None:
    response = analyst_client.request(method, path, json={})

    assert response.status_code == 403
    assert response.json()["detail"] == "Administrator role required"


def test_forbidden_is_answered_before_not_found(analyst_client: TestClient) -> None:
    """Um analista não deve conseguir descobrir que ids existem através de 403 vs 404."""
    assert analyst_client.delete("/assets/424242").status_code == 403


def test_analysts_can_still_do_their_normal_work(analyst_client: TestClient) -> None:
    asset = analyst_client.post("/assets", json={"name": "srv", "asset_type": "server"})
    vuln = analyst_client.post("/vulnerabilities", json={"title": "v", "severity": "low"})
    incident = analyst_client.post("/incidents", json={"title": "i", "severity": "low"})
    iid = incident.json()["id"]

    assert asset.status_code == vuln.status_code == incident.status_code == 201
    transition = analyst_client.post(
        f"/incidents/{iid}/transitions", json={"to_status": "investigating"}
    )
    assert transition.status_code == 200
    assert (
        analyst_client.patch(f"/assets/{asset.json()['id']}", json={"owner": "ops"}).status_code
        == 200
    )
    assert analyst_client.get("/dashboard/summary").status_code == 200
    # ... e o audit trail regista o analista, não outra pessoa
    history = analyst_client.get(f"/incidents/{iid}/history").json()
    assert {entry["changed_by"] for entry in history} == {ANALYST_EMAIL}


def test_admins_can_delete_assets_and_vulnerabilities(client: TestClient) -> None:
    asset = client.post("/assets", json={"name": "srv", "asset_type": "server"}).json()
    vuln = client.post("/vulnerabilities", json={"title": "v", "severity": "low"}).json()

    assert client.delete(f"/assets/{asset['id']}").status_code == 204
    assert client.delete(f"/vulnerabilities/{vuln['id']}").status_code == 204


def test_a_role_change_takes_effect_immediately(
    analyst_client: TestClient, analyst_user: User, db: Session
) -> None:
    assert analyst_client.get("/users").status_code == 403

    analyst_user.role = UserRole.admin  # o mesmo token, agora com outro papel
    db.commit()

    assert analyst_client.get("/users").status_code == 200


# --- criar utilizadores ---------------------------------------------------------


def test_admin_creates_a_user_who_can_log_in(client: TestClient, anonymous_client: TestClient):
    response = create_user(client, email="  New.User@Example.com ", role="analyst")

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "new.user@example.com"
    assert body["role"] == "analyst" and body["is_active"] is True
    assert "password" not in body and "hashed_password" not in body

    login = anonymous_client.post(
        "/auth/login", data={"username": "new.user@example.com", "password": STRONG_PASSWORD}
    )
    assert login.status_code == 200


def test_role_defaults_to_analyst(client: TestClient) -> None:
    assert create_user(client).json()["role"] == "analyst"


def test_duplicate_email_is_a_conflict(client: TestClient) -> None:
    assert create_user(client).status_code == 201

    duplicate = create_user(client, email="NEW.USER@example.com")

    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"password": "short"},
        {"password": "x" * 11},
        {"password": "é" * 40},  # 80 bytes: passa o comprimento mas não cabe no bcrypt
        {"email": "not-an-email"},
        {"full_name": ""},
        {"role": "superuser"},
    ],
)
def test_invalid_users_are_rejected(client: TestClient, overrides: dict) -> None:
    assert create_user(client, **overrides).status_code == 422


def test_list_users_never_exposes_password_hashes(client: TestClient, test_user: User) -> None:
    create_user(client)

    users = client.get("/users").json()

    assert {u["email"] for u in users} == {test_user.email, "new.user@example.com"}
    assert all("hashed_password" not in u and "password" not in u for u in users)


# --- alterar utilizadores -------------------------------------------------------


def test_admin_can_change_role_and_name(client: TestClient) -> None:
    user_id = create_user(client).json()["id"]

    response = client.patch(f"/users/{user_id}", json={"role": "admin", "full_name": " Renamed "})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
    assert response.json()["full_name"] == "Renamed"


def test_deactivated_user_loses_access_immediately(
    client: TestClient, analyst_client: TestClient, analyst_user: User
) -> None:
    assert analyst_client.get("/incidents").status_code == 200

    assert client.patch(f"/users/{analyst_user.id}", json={"is_active": False}).status_code == 200

    assert analyst_client.get("/incidents").status_code == 401


def test_reactivated_user_gets_access_back(
    client: TestClient, analyst_client: TestClient, analyst_user: User
) -> None:
    client.patch(f"/users/{analyst_user.id}", json={"is_active": False})
    client.patch(f"/users/{analyst_user.id}", json={"is_active": True})

    assert analyst_client.get("/incidents").status_code == 200


def test_update_validates_input_and_missing_user(client: TestClient, analyst_user: User) -> None:
    url = f"/users/{analyst_user.id}"

    assert client.patch(url, json={"role": None}).status_code == 422
    assert client.patch(url, json={"is_active": None}).status_code == 422
    assert client.patch(url, json={"role": "superuser"}).status_code == 422
    assert client.patch("/users/424242", json={"role": "admin"}).status_code == 404


def test_the_only_admin_cannot_demote_or_deactivate_themselves(
    client: TestClient, test_user: User
) -> None:
    url = f"/users/{test_user.id}"

    demote = client.patch(url, json={"role": "analyst"})
    deactivate = client.patch(url, json={"is_active": False})

    assert demote.status_code == deactivate.status_code == 409
    assert "last active administrator" in demote.json()["detail"]
    assert client.get("/users").status_code == 200  # continua administrador


def test_with_two_admins_one_can_be_demoted(client: TestClient, test_user: User) -> None:
    second = create_user(client, role="admin").json()

    assert client.patch(f"/users/{second['id']}", json={"role": "analyst"}).status_code == 200
    # agora o teste_user volta a ser o único admin
    assert client.patch(f"/users/{test_user.id}", json={"role": "analyst"}).status_code == 409


def test_an_inactive_admin_does_not_count_as_an_administrator(
    client: TestClient, test_user: User
) -> None:
    second = create_user(client, role="admin").json()
    client.patch(f"/users/{second['id']}", json={"is_active": False})

    assert client.patch(f"/users/{test_user.id}", json={"role": "analyst"}).status_code == 409


def test_changes_that_keep_admin_status_are_allowed_for_the_only_admin(
    client: TestClient, test_user: User
) -> None:
    response = client.patch(f"/users/{test_user.id}", json={"full_name": "Renamed Admin"})

    assert response.status_code == 200
