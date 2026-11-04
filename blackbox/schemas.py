from datetime import datetime
from pathlib import PurePosixPath
from uuid import UUID
from .redaction import redact

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Frame(BaseModel):
    model_config = ConfigDict(extra='forbid')
    path: str = Field(min_length=1, max_length=1024)
    line: int = Field(ge=1, le=10_000_000)
    function: str = Field(min_length=1, max_length=256)

    @field_validator('path')
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if ('\\' in value or ':' in value or any(ord(c) < 32 for c in value) or path.is_absolute()
                or any(p in ('', '..', '.') for p in value.split('/')) or value.startswith('-')
                or redact(value) != value):
            raise ValueError('path must be a repository-relative POSIX path')
        return value


class Event(BaseModel):
    model_config = ConfigDict(extra='forbid')
    event_id: UUID
    occurred_at: datetime
    commit: str = Field(pattern=r'^[0-9a-f]{40}$')
    exception_type: str = Field(min_length=1, max_length=256, pattern=r'^[A-Za-z_][A-Za-z0-9_.]*$')
    message: str = Field(max_length=8192)
    traceback: str = Field(max_length=65536)
    frames: list[Frame] = Field(min_length=1, max_length=100)

    @field_validator('occurred_at')
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError('timestamp must include a timezone')
        return value
