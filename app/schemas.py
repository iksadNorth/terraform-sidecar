from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class LockInfo(BaseModel):
    status: Literal["apply_running", "destroy_running", "git_clone"]
    started_at: datetime
    message: str


class ProjectSummary(BaseModel):
    id: str
    initialized: bool
    has_state: bool
    lock_info: LockInfo | None = None


class ProjectStatus(ProjectSummary):
    path: str


class ApplyRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)
    message: str | None = None


class DestroyRequest(BaseModel):
    variables: dict[str, str] = Field(default_factory=dict)
    message: str | None = None


class ApplyResponse(BaseModel):
    project_id: str
    action: Literal["apply"]
    output: str


class DestroyResponse(BaseModel):
    project_id: str
    action: Literal["destroy"]
    output: str


class GitCloneRequest(BaseModel):
    repo_url: str = Field(..., alias="git_url")
    branch: str | None = None
    depth: int | None = None


class GitCloneResponse(BaseModel):
    project_id: str
    repo_url: str
    branch: str | None = None
    initialized: bool

