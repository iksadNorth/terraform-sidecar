from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status

from .schemas import LockInfo


class TerraformError(RuntimeError):
    """Terraform 실행 도중 발생한 일반 에러."""

    def __init__(self, message: str, *, output: str | None = None) -> None:
        super().__init__(message)
        self.output = output


class ProjectNotFoundError(FileNotFoundError):
    """요청한 프로젝트가 존재하지 않을 때."""

    def __init__(self, project_id: str) -> None:
        super().__init__(f"Terraform project '{project_id}' not found")
        self.project_id = project_id


class ProjectLockedError(RuntimeError):
    """이미 작업 중인 프로젝트에 대해 apply/destroy 요청이 들어왔을 때."""

    def __init__(self, lock_info: LockInfo) -> None:
        super().__init__("Terraform project is locked")
        self.lock_info = lock_info


def raise_http_exception(exc: Exception) -> None:
    """예외를 FastAPI HTTPException 형태로 변환."""

    if isinstance(exc, ProjectNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"reason": "project_not_found", "message": str(exc)},
        ) from exc

    if isinstance(exc, ProjectLockedError):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"reason": "project_locked", "lock_info": exc.lock_info.model_dump()},
        ) from exc

    if isinstance(exc, TerraformError):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "reason": "terraform_error",
                "message": str(exc),
                "output": exc.output,
            },
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail={"reason": "unexpected_error", "message": str(exc)},
    ) from exc

