"""Create the first organization, project, and API key.

Run after migrations with:
    python -m apps.cli.bootstrap --organization Acme --slug acme --project Billing
"""

import argparse
import secrets
import sys

from sqlalchemy import select

from apps.api.database import SessionLocal
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import ApiKey, Project
from apps.shared.security.api_keys import hash_api_key


def create_api_key() -> str:
    return f"flk_{secrets.token_urlsafe(32)}"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap a FlowLedger project and API key.")
    parser.add_argument("--organization", required=True, help="Organization display name")
    parser.add_argument("--slug", required=True, help="Unique organization slug")
    parser.add_argument("--project", required=True, help="Initial project name")
    parser.add_argument("--key-name", default="bootstrap", help="Human-readable API key name")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with SessionLocal() as session:
        existing = session.scalar(select(Organization).where(Organization.slug == args.slug))
        if existing is not None:
            print(f"Organization slug already exists: {args.slug}", file=sys.stderr)
            return 1

        organization = Organization(name=args.organization, slug=args.slug)
        session.add(organization)
        session.flush()
        project = Project(organization_id=organization.id, name=args.project)
        session.add(project)
        session.flush()
        raw_key = create_api_key()
        session.add(
            ApiKey(
                project_id=project.id,
                key_hash=hash_api_key(raw_key),
                name=args.key_name,
            )
        )
        session.commit()

    print("Bootstrap complete. Store this API key now; it cannot be displayed again.")
    print(f"Project ID: {project.id}")
    print(f"API key: {raw_key}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
