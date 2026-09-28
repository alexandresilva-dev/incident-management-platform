from fastapi.testclient import TestClient


def make_asset(client: TestClient, name: str = "srv-web-01") -> dict:
    response = client.post("/assets", json={"name": name, "asset_type": "server"})
    assert response.status_code == 201
    return response.json()


def make_vulnerability(client: TestClient, **overrides) -> dict:
    payload = {"title": "OpenSSH RCE", "severity": "high", **overrides}
    response = client.post("/vulnerabilities", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# --- create ---------------------------------------------------------------


def test_create_vulnerability_applies_defaults(client: TestClient) -> None:
    vuln = make_vulnerability(client)

    assert vuln["status"] == "open"
    assert vuln["asset_id"] is None
    assert vuln["cvss_score"] is None


def test_severity_is_derived_from_cvss_when_omitted(client: TestClient) -> None:
    response = client.post("/vulnerabilities", json={"title": "xz backdoor", "cvss_score": 10.0})

    assert response.status_code == 201
    assert response.json()["severity"] == "critical"


def test_explicit_severity_wins_over_derivation(client: TestClient) -> None:
    vuln = make_vulnerability(client, cvss_score=9.8, severity="low")

    assert vuln["severity"] == "low"
    assert vuln["cvss_score"] == 9.8


def test_cve_id_is_normalised_to_uppercase(client: TestClient) -> None:
    vuln = make_vulnerability(client, cve_id="cve-2024-3094")

    assert vuln["cve_id"] == "CVE-2024-3094"


def test_create_vulnerability_rejects_invalid_payload(client: TestClient) -> None:
    invalid_payloads = [
        {"severity": "high"},  # missing title
        {"title": "x"},  # neither severity nor cvss
        {"title": "x", "severity": "high", "cve_id": "CVE-24-1"},  # bad CVE format
        {"title": "x", "severity": "high", "cve_id": "not-a-cve"},
        {"title": "x", "cvss_score": 10.1},  # above range
        {"title": "x", "cvss_score": -0.1},  # below range
        {"title": "x", "cvss_score": 5.55},  # more than 1 decimal place
        {"title": "x", "severity": "catastrophic"},
        {"title": "x", "severity": "high", "status": "ignored"},
    ]
    for payload in invalid_payloads:
        response = client.post("/vulnerabilities", json=payload)
        assert response.status_code == 422, payload


def test_create_with_unknown_asset_returns_422(client: TestClient) -> None:
    response = client.post(
        "/vulnerabilities", json={"title": "x", "severity": "low", "asset_id": 424242}
    )

    assert response.status_code == 422
    assert "424242" in response.json()["detail"]


def test_create_linked_to_asset(client: TestClient) -> None:
    asset = make_asset(client)

    vuln = make_vulnerability(client, asset_id=asset["id"])

    assert vuln["asset_id"] == asset["id"]


# --- read -----------------------------------------------------------------


def test_get_vulnerability_and_404(client: TestClient) -> None:
    created = make_vulnerability(client)

    assert client.get(f"/vulnerabilities/{created['id']}").json() == created
    assert client.get("/vulnerabilities/424242").status_code == 404


def test_list_vulnerabilities_filters(client: TestClient) -> None:
    asset = make_asset(client)
    make_vulnerability(client, title="a", severity="critical", cve_id="CVE-2024-0001", asset_id=asset["id"])
    make_vulnerability(client, title="b", severity="low", status="patched")
    make_vulnerability(client, title="c", severity="critical")

    def titles(**params) -> list[str]:
        response = client.get("/vulnerabilities", params=params)
        assert response.status_code == 200
        return [v["title"] for v in response.json()]

    assert titles() == ["a", "b", "c"]
    assert titles(severity="critical") == ["a", "c"]
    assert titles(status="patched") == ["b"]
    assert titles(asset_id=asset["id"]) == ["a"]
    assert titles(cve_id="cve-2024-0001") == ["a"]  # case-insensitive
    assert titles(limit=1, skip=2) == ["c"]


# --- update ---------------------------------------------------------------


def test_patch_status_and_asset(client: TestClient) -> None:
    asset = make_asset(client)
    vuln = make_vulnerability(client)

    response = client.patch(
        f"/vulnerabilities/{vuln['id']}", json={"status": "patched", "asset_id": asset["id"]}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "patched"
    assert response.json()["asset_id"] == asset["id"]
    assert response.json()["title"] == vuln["title"]


def test_patch_rejects_null_for_required_and_unknown_asset(client: TestClient) -> None:
    vuln = make_vulnerability(client)
    url = f"/vulnerabilities/{vuln['id']}"

    assert client.patch(url, json={"severity": None}).status_code == 422
    assert client.patch(url, json={"asset_id": 424242}).status_code == 422
    assert client.patch("/vulnerabilities/424242", json={"title": "x"}).status_code == 404


# --- delete ---------------------------------------------------------------


def test_delete_vulnerability(client: TestClient) -> None:
    vuln = make_vulnerability(client)

    assert client.delete(f"/vulnerabilities/{vuln['id']}").status_code == 204
    assert client.get(f"/vulnerabilities/{vuln['id']}").status_code == 404
    assert client.delete(f"/vulnerabilities/{vuln['id']}").status_code == 404


def test_deleting_asset_keeps_vulnerability_without_asset(client: TestClient) -> None:
    asset = make_asset(client)
    vuln = make_vulnerability(client, asset_id=asset["id"])

    assert client.delete(f"/assets/{asset['id']}").status_code == 204

    remaining = client.get(f"/vulnerabilities/{vuln['id']}")
    assert remaining.status_code == 200
    assert remaining.json()["asset_id"] is None
