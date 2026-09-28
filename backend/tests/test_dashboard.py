from fastapi.testclient import TestClient


def create(client: TestClient, path: str, **payload) -> dict:
    response = client.post(path, json=payload)
    assert response.status_code == 201, response.text
    return response.json()


def test_summary_of_empty_database_has_every_key_at_zero(client: TestClient) -> None:
    summary = client.get("/dashboard/summary").json()

    assert summary["incidents"]["total"] == 0
    assert summary["incidents"]["active"] == 0
    assert summary["incidents"]["by_status"] == {
        "open": 0, "investigating": 0, "mitigated": 0, "resolved": 0, "closed": 0,
    }
    assert summary["incidents"]["by_priority"] == {"P1": 0, "P2": 0, "P3": 0, "P4": 0}
    assert summary["assets"] == {
        "total": 0, "by_criticality": {"low": 0, "medium": 0, "high": 0, "critical": 0},
    }
    assert summary["vulnerabilities"]["by_status"] == {
        "open": 0, "mitigated": 0, "patched": 0, "accepted": 0,
    }


def test_summary_counts_everything(client: TestClient) -> None:
    payments = create(client, "/assets", name="payments-db", asset_type="database", criticality="critical")
    create(client, "/assets", name="laptop", asset_type="workstation", criticality="low")
    create(client, "/vulnerabilities", title="v1", severity="critical", asset_id=payments["id"])
    create(client, "/vulnerabilities", title="v2", severity="low", status="patched")
    create(client, "/incidents", title="a", severity="high", asset_ids=[payments["id"]])
    create(client, "/incidents", title="b", severity="low")
    closing = create(client, "/incidents", title="c", severity="medium")
    for target in ("investigating", "mitigated", "resolved", "closed"):
        client.post(f"/incidents/{closing['id']}/transitions", json={"to_status": target})

    summary = client.get("/dashboard/summary").json()

    incidents = summary["incidents"]
    assert incidents["total"] == 3
    assert incidents["active"] == 2
    assert incidents["by_status"]["open"] == 2 and incidents["by_status"]["closed"] == 1
    assert incidents["by_severity"] == {"low": 1, "medium": 1, "high": 1, "critical": 0}
    assert incidents["by_priority"] == {"P1": 1, "P2": 0, "P3": 1, "P4": 1}  # high + critical asset -> P1
    assert summary["assets"]["total"] == 2
    assert summary["assets"]["by_criticality"]["critical"] == 1
    assert summary["vulnerabilities"]["total"] == 2
    assert summary["vulnerabilities"]["by_status"]["patched"] == 1
    assert summary["vulnerabilities"]["by_severity"]["critical"] == 1
