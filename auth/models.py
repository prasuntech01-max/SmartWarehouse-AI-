"""Data models for authentication and session handling.
Only lightweight dataclasses; actual persistence is via persistence.repo.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(frozen=True)
class AuthUser:
    id: int
    username: str
    role: str  # ADMIN, OPERATOR, VIEWER
    created_at: datetime
    last_login: Optional[datetime]

@dataclass(frozen=True)
class AuthSession:
    token: str
    user_id: int
    issued_at: datetime
    last_activity: datetime
    expires_at: datetime
