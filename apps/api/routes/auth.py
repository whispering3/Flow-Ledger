from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select

from apps.api.dependencies import CurrentUser, DbSession
from apps.modules.identity.models import Membership, MembershipRole, RefreshToken, User
from apps.modules.organizations.models import Organization
from apps.modules.projects.models import ApiKey, Project
from apps.shared.security.api_keys import hash_api_key
from apps.shared.security.passwords import hash_password, verify_password
from apps.shared.security.tokens import (
    REFRESH_TOKEN_DAYS,
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["authentication"])


class RegisterInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)
    organization_name: str = Field(min_length=1, max_length=200)
    organization_slug: str = Field(min_length=3, max_length=100, pattern=r"^[a-z0-9-]+$")
    project_name: str = Field(min_length=1, max_length=200)


class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class RefreshInput(BaseModel):
    refresh_token: str = Field(min_length=20, max_length=512)


class TokenOutput(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RegistrationOutput(TokenOutput):
    project_id: str
    api_key: str


class UserOutput(BaseModel):
    id: str
    email: EmailStr


def issue_tokens(db: DbSession, user: User) -> TokenOutput:
    raw_refresh = create_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            token_hash=hash_refresh_token(raw_refresh),
            expires_at=datetime.now(UTC) + timedelta(days=REFRESH_TOKEN_DAYS),
        )
    )
    db.commit()
    return TokenOutput(access_token=create_access_token(user.id), refresh_token=raw_refresh)


@router.post("/register", response_model=RegistrationOutput, status_code=status.HTTP_201_CREATED)
def register(body: RegisterInput, db: DbSession) -> RegistrationOutput:
    normalized_email = body.email.lower()
    if db.scalar(select(User.id).where(User.email == normalized_email)) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    if (
        db.scalar(select(Organization.id).where(Organization.slug == body.organization_slug))
        is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Organization slug already in use"
        )
    user = User(email=normalized_email, password_hash=hash_password(body.password))
    db.add(user)
    db.flush()
    organization = Organization(name=body.organization_name, slug=body.organization_slug)
    db.add(organization)
    db.flush()
    db.add(Membership(organization_id=organization.id, user_id=user.id, role=MembershipRole.OWNER))
    project = Project(organization_id=organization.id, name=body.project_name)
    db.add(project)
    db.flush()
    import secrets

    raw_api_key = f"flk_{secrets.token_urlsafe(32)}"
    db.add(ApiKey(project_id=project.id, key_hash=hash_api_key(raw_api_key), name="default"))
    db.commit()
    tokens = issue_tokens(db, user)
    return RegistrationOutput(
        **tokens.model_dump(),
        project_id=str(project.id),
        api_key=raw_api_key,
    )


@router.post("/login", response_model=TokenOutput)
def login(body: LoginInput, db: DbSession) -> TokenOutput:
    user = db.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )
    return issue_tokens(db, user)


@router.post("/refresh", response_model=TokenOutput)
def refresh(body: RefreshInput, db: DbSession) -> TokenOutput:
    now = datetime.now(UTC)
    stored = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_refresh_token(body.refresh_token)
        )
    )
    if stored is None or stored.revoked_at is not None or stored.expires_at <= now:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    stored.revoked_at = now
    user = db.get(User, stored.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    return issue_tokens(db, user)


@router.get("/me", response_model=UserOutput)
def me(user: CurrentUser) -> UserOutput:
    return UserOutput(id=str(user.id), email=user.email)
