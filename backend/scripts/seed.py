"""Popula a base de dados com dados de demonstração.

Uso (dentro do contentor da API):
    docker compose exec api python -m scripts.seed

Recusa correr se já existirem dados, para nunca duplicar nem misturar.
"""

from decimal import Decimal

from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models import Asset, Incident, Vulnerability
from app.models.enums import (
    AssetType,
    Criticality,
    IncidentCategory,
    IncidentStatus,
    Severity,
    VulnerabilityStatus,
)
from app.schemas.incident import IncidentCreate
from app.services.incidents import create_incident, transition_incident

S = IncidentStatus

ASSETS = [
    ("payments-db", AssetType.database, Criticality.critical, "10.20.0.5", "Payments team"),
    (
        "core-vpn-gateway",
        AssetType.network_device,
        Criticality.critical,
        "10.0.0.1",
        "Network team",
    ),
    ("web-frontend-01", AssetType.server, Criticality.high, "10.10.0.11", "Platform team"),
    ("web-frontend-02", AssetType.server, Criticality.high, "10.10.0.12", "Platform team"),
    ("aws-s3-backups", AssetType.cloud_service, Criticality.high, None, "Infrastructure team"),
    ("crm-app", AssetType.application, Criticality.medium, "10.30.0.8", "Sales IT"),
    ("hr-fileserver", AssetType.server, Criticality.medium, "10.40.0.3", "HR IT"),
    ("dev-laptop-014", AssetType.workstation, Criticality.low, None, "Engineering"),
]

# (cve, title, cvss, severity, status, asset)
VULNERABILITIES = [
    (
        "CVE-2024-3094",
        "XZ Utils backdoor in liblzma",
        "10.0",
        Severity.critical,
        VulnerabilityStatus.open,
        "web-frontend-01",
    ),
    (
        "CVE-2024-21762",
        "FortiOS out-of-bounds write",
        "9.6",
        Severity.critical,
        VulnerabilityStatus.open,
        "core-vpn-gateway",
    ),
    (
        "CVE-2024-6387",
        "OpenSSH regreSSHion race condition",
        "8.1",
        Severity.high,
        VulnerabilityStatus.mitigated,
        "core-vpn-gateway",
    ),
    (
        "CVE-2023-44487",
        "HTTP/2 Rapid Reset",
        "7.5",
        Severity.high,
        VulnerabilityStatus.open,
        "web-frontend-02",
    ),
    (
        "CVE-2021-44228",
        "Log4Shell remote code execution",
        "10.0",
        Severity.critical,
        VulnerabilityStatus.patched,
        "hr-fileserver",
    ),
    (
        "CVE-2023-4863",
        "libwebp heap buffer overflow",
        "8.8",
        Severity.high,
        VulnerabilityStatus.patched,
        "dev-laptop-014",
    ),
    (
        "CVE-2022-22965",
        "Spring4Shell",
        "9.8",
        Severity.critical,
        VulnerabilityStatus.accepted,
        "crm-app",
    ),
    (
        None,
        "Backup bucket allows public listing",
        None,
        Severity.high,
        VulnerabilityStatus.open,
        "aws-s3-backups",
    ),
]

# (title, category, severity, [assets], [cves/titles], [(to_status, comment), ...])
INCIDENTS = [
    (
        "Ransomware detected on HR file server",
        IncidentCategory.malware,
        Severity.critical,
        ["hr-fileserver"],
        ["CVE-2021-44228"],
        [
            (S.investigating, "Host isolated from the network"),
            (S.mitigated, "Encrypted shares restored from backup"),
        ],
    ),
    (
        "Suspicious VPN logins from unusual locations",
        IncidentCategory.unauthorized_access,
        Severity.high,
        ["core-vpn-gateway"],
        ["CVE-2024-21762"],
        [(S.investigating, "Reviewing authentication logs")],
    ),
    (
        "Data exfiltration attempt from payments database",
        IncidentCategory.data_breach,
        Severity.critical,
        ["payments-db"],
        [],
        [],
    ),
    (
        "Public S3 bucket exposes backup metadata",
        IncidentCategory.misconfiguration,
        Severity.high,
        ["aws-s3-backups"],
        ["Backup bucket allows public listing"],
        [],
    ),
    (
        "Phishing campaign targeting the finance team",
        IncidentCategory.phishing,
        Severity.medium,
        [],
        [],
        [
            (S.investigating, "Collecting reported emails"),
            (S.mitigated, "Sender domain blocked at the mail gateway"),
            (S.resolved, "No credentials were submitted"),
        ],
    ),
    (
        "Outdated OpenSSH on VPN gateway",
        IncidentCategory.misconfiguration,
        Severity.medium,
        ["core-vpn-gateway"],
        ["CVE-2024-6387"],
        [
            (S.investigating, None),
            (S.mitigated, "Rate limiting enabled while patching is scheduled"),
        ],
    ),
    (
        "DDoS against public web frontends",
        IncidentCategory.denial_of_service,
        Severity.high,
        ["web-frontend-01", "web-frontend-02"],
        ["CVE-2023-44487"],
        [
            (S.investigating, "Traffic spike confirmed"),
            (S.mitigated, "Rate limiting and upstream filtering applied"),
            (S.resolved, "Traffic back to baseline"),
            (S.closed, "Post-incident review completed"),
        ],
    ),
    (
        "Malware alert on developer laptop",
        IncidentCategory.malware,
        Severity.low,
        ["dev-laptop-014"],
        ["CVE-2023-4863"],
        [
            (S.investigating, None),
            (S.mitigated, "Laptop reimaged"),
            (S.resolved, None),
            (S.closed, "False positive after review"),
        ],
    ),
]


def main() -> None:
    with SessionLocal() as db:
        existing = db.scalar(select(func.count()).select_from(Asset)) + db.scalar(
            select(func.count()).select_from(Incident)
        )
        if existing:
            raise SystemExit("Database already has data; refusing to seed. Nothing changed.")

        assets = {}
        for name, asset_type, criticality, ip, owner in ASSETS:
            assets[name] = Asset(
                name=name,
                asset_type=asset_type,
                criticality=criticality,
                ip_address=ip,
                owner=owner,
            )
        db.add_all(assets.values())

        vulnerabilities = {}
        for cve, title, cvss, severity, status, asset_name in VULNERABILITIES:
            vuln = Vulnerability(
                cve_id=cve,
                title=title,
                severity=severity,
                status=status,
                cvss_score=Decimal(cvss) if cvss else None,
                asset=assets[asset_name],
            )
            vulnerabilities[cve or title] = vuln
        db.add_all(vulnerabilities.values())
        db.commit()

        for title, category, severity, asset_names, vuln_keys, steps in INCIDENTS:
            incident = create_incident(
                db,
                IncidentCreate(
                    title=title,
                    category=category,
                    severity=severity,
                    asset_ids=[assets[n].id for n in asset_names],
                    vulnerability_ids=[vulnerabilities[k].id for k in vuln_keys],
                ),
            )
            for target, comment in steps:
                transition_incident(db, incident, target, comment=comment)

        print(
            f"Seeded {len(ASSETS)} assets, {len(VULNERABILITIES)} vulnerabilities "
            f"and {len(INCIDENTS)} incidents."
        )


if __name__ == "__main__":
    main()
