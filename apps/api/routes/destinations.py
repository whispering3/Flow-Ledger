from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select

from apps.api.dependencies import DbSession, ProjectDependency
from apps.modules.destinations.models import Destination
from apps.shared.security.secrets import encrypt_secret, generate_signing_secret

router = APIRouter(prefix="/destinations", tags=["destinations"])


def validate_http_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("URL must be an absolute HTTP or HTTPS URL")
    if parsed.username or parsed.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    return value


class DestinationInput(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    event_types: list[str] = Field(default_factory=list, max_length=50)
    signing_secret: str | None = Field(default=None, min_length=32, max_length=200)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        return validate_http_url(value)

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, values: list[str]) -> list[str]:
        if len(set(values)) != len(values):
            raise ValueError("event_types must not contain duplicates")
        if any(not value or len(value) > 120 for value in values):
            raise ValueError("event_types must contain non-empty values up to 120 characters")
        return values


class DestinationPatch(BaseModel):
    url: str | None = Field(default=None, min_length=1, max_length=2048)
    event_types: list[str] | None = Field(default=None, max_length=50)
    enabled: bool | None = None
    signing_secret: str | None = Field(default=None, min_length=32, max_length=200)

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        return validate_http_url(value) if value is not None else value

    @field_validator("event_types")
    @classmethod
    def validate_event_types(cls, values: list[str] | None) -> list[str] | None:
        if values is not None and len(set(values)) != len(values):
            raise ValueError("event_types must not contain duplicates")
        return values


class DestinationOutput(BaseModel):
    id: UUID
    url: str
    enabled: bool
    event_types: list[str]

    model_config = {"from_attributes": True}


class DestinationCreatedOutput(DestinationOutput):
    signing_secret: str


@router.post("", response_model=DestinationCreatedOutput, status_code=status.HTTP_201_CREATED)
def create_destination(
    body: DestinationInput, db: DbSession, project: ProjectDependency
) -> DestinationCreatedOutput:
    signing_secret = body.signing_secret or generate_signing_secret()
    destination = Destination(
        project_id=project.id,
        url=body.url,
        event_types=body.event_types,
        signing_secret_ciphertext=encrypt_secret(signing_secret),
    )
    db.add(destination)
    db.commit()
    db.refresh(destination)
    return DestinationCreatedOutput(
        id=destination.id,
        url=destination.url,
        enabled=destination.enabled,
        event_types=destination.event_types,
        signing_secret=signing_secret,
    )


@router.get("", response_model=list[DestinationOutput])
def list_destinations(db: DbSession, project: ProjectDependency) -> list[Destination]:
    return list(
        db.scalars(
            select(Destination)
            .where(Destination.project_id == project.id)
            .order_by(Destination.created_at.desc())
        )
    )


@router.patch("/{destination_id}", response_model=DestinationOutput)
def update_destination(
    destination_id: UUID, body: DestinationPatch, db: DbSession, project: ProjectDependency
) -> Destination:
    destination = db.scalar(
        select(Destination).where(
            Destination.id == destination_id, Destination.project_id == project.id
        )
    )
    if destination is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destination not found")
    changes = body.model_dump(exclude_unset=True)
    signing_secret = changes.pop("signing_secret", None)
    if signing_secret is not None:
        destination.signing_secret_ciphertext = encrypt_secret(signing_secret)
    for field, value in changes.items():
        setattr(destination, field, value)
    db.commit()
    db.refresh(destination)
    return destination
