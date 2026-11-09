from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from apps.api.database import get_db
from apps.modules.identity.models import User
from apps.modules.projects.models import Project
from apps.shared.security.api_keys import authenticate_api_key
from apps.shared.security.tokens import parse_access_token

DbSession = Annotated[Session, Depends(get_db)]
ApiKeyHeader = Annotated[str, Header(alias="X-API-Key", min_length=1)]


def current_project(x_api_key: ApiKeyHeader, db: DbSession) -> Project:
    project = authenticate_api_key(db, x_api_key)
    if project is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    return project


ProjectDependency = Annotated[Project, Depends(current_project)]

bearer = HTTPBearer(auto_error=False)


def current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: DbSession,
) -> User:
    user_id = parse_access_token(credentials.credentials) if credentials else None
    user = db.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token")
    return user


CurrentUser = Annotated[User, Depends(current_user)]
