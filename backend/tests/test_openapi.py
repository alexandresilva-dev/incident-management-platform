from fastapi.testclient import TestClient

from app.main import app

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}
PUBLIC = {("get", "/health"), ("post", "/auth/login")}


def schema() -> dict:
    return app.openapi()


def test_api_has_a_description_and_version() -> None:
    info = schema()["info"]

    assert info["version"]
    assert "Authentication" in info["description"]
    assert "Incident workflow" in info["description"]


def test_every_tag_used_by_an_operation_is_described() -> None:
    documented = {tag["name"]: tag.get("description") for tag in schema()["tags"]}
    used = {
        tag
        for operations in schema()["paths"].values()
        for method, operation in operations.items()
        if method in HTTP_METHODS
        for tag in operation.get("tags", [])
    }

    assert used <= set(documented)
    assert all(documented[tag] for tag in used)


def test_every_protected_operation_documents_401() -> None:
    for path, operations in schema()["paths"].items():
        for method, operation in operations.items():
            if method in HTTP_METHODS and (method, path) not in PUBLIC:
                assert "401" in operation["responses"], f"{method.upper()} {path}"


def test_operations_with_a_path_id_document_404() -> None:
    for path, operations in schema()["paths"].items():
        if "{" not in path:
            continue
        for method, operation in operations.items():
            if method in HTTP_METHODS:
                assert "404" in operation["responses"], f"{method.upper()} {path}"


def test_every_operation_has_a_description() -> None:
    for path, operations in schema()["paths"].items():
        for method, operation in operations.items():
            if method in HTTP_METHODS:
                assert operation.get("description"), f"{method.upper()} {path} has no description"


def test_transition_documents_the_409_body(anonymous_client: TestClient) -> None:
    operation = schema()["paths"]["/incidents/{incident_id}/transitions"]["post"]

    example = operation["responses"]["409"]["content"]["application/json"]["example"]

    assert example["allowed_transitions"] == ["investigating"]


def test_docs_pages_are_served(anonymous_client: TestClient) -> None:
    assert anonymous_client.get("/docs").status_code == 200
    assert anonymous_client.get("/openapi.json").status_code == 200


ADMIN_OPERATIONS = {
    ("delete", "/assets/{asset_id}"),
    ("delete", "/vulnerabilities/{vulnerability_id}"),
    ("get", "/users"),
    ("post", "/users"),
    ("patch", "/users/{user_id}"),
}


def test_admin_only_operations_document_403() -> None:
    paths = schema()["paths"]
    for method, path in ADMIN_OPERATIONS:
        assert "403" in paths[path][method]["responses"], f"{method.upper()} {path}"


def test_only_the_known_admin_operations_document_403() -> None:
    """Se aparecer um 403 novo, este teste obriga a decidir se é mesmo só para admins."""
    documented = {
        (method, path)
        for path, operations in schema()["paths"].items()
        for method, operation in operations.items()
        if method in HTTP_METHODS and "403" in operation["responses"]
    }

    assert documented == ADMIN_OPERATIONS


def test_login_documents_429() -> None:
    assert "429" in schema()["paths"]["/auth/login"]["post"]["responses"]
