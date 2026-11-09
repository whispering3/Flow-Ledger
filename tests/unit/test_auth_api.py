from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.api.database import Base, get_db
from apps.api.main import app


def test_registration_login_and_profile_flow() -> None:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as client:
            registration = client.post(
                "/v1/auth/register",
                json={
                    "email": "owner@example.com",
                    "password": "correct-horse-battery-staple",
                    "organization_name": "Acme",
                    "organization_slug": "acme",
                    "project_name": "Billing",
                },
            )
            assert registration.status_code == 201
            payload = registration.json()
            assert payload["api_key"].startswith("flk_")

            profile = client.get(
                "/v1/auth/me",
                headers={"Authorization": f"Bearer {payload['access_token']}"},
            )
            assert profile.status_code == 200
            assert profile.json()["email"] == "owner@example.com"

            login = client.post(
                "/v1/auth/login",
                json={"email": "owner@example.com", "password": "correct-horse-battery-staple"},
            )
            assert login.status_code == 200
            assert login.json()["token_type"] == "bearer"
            assert login.json()["refresh_token"] != payload["refresh_token"]
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
