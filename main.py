from __future__ import annotations

from fastapi import FastAPI

from app.config import settings
from app.exceptions import raise_http_exception
from app.locks import LockManager
from app.schemas import (
    ApplyRequest,
    ApplyResponse,
    DestroyRequest,
    DestroyResponse,
    GitCloneRequest,
    GitCloneResponse,
    ProjectStatus,
    ProjectSummary,
)
from app.terraform import TerraformManager

app = FastAPI(
    title="Terraform Sidecar",
    description="Terraform 프로젝트를 REST API로 관리하는 FastAPI 서비스",
)

lock_manager = LockManager(settings.lock_dir, settings.lock_ttl_seconds)
terraform_manager = TerraformManager(settings, lock_manager)


@app.on_event("startup")
async def startup_event() -> None:
    settings.ensure_directories()
    if settings.startup_init_enabled:
        terraform_manager.initialize_projects()


@app.get("/tfpjts", response_model=list[ProjectSummary])
async def list_projects() -> list[ProjectSummary]:
    try:
        statuses = terraform_manager.list_projects()
        return [
            ProjectSummary(
                id=status.id,
                initialized=status.initialized,
                has_state=status.has_state,
                lock_info=status.lock_info,
            )
            for status in statuses
        ]
    except Exception as exc:
        raise_http_exception(exc)


@app.get("/tfpjts/{project_id}", response_model=ProjectStatus)
async def get_project(project_id: str) -> ProjectStatus:
    try:
        return terraform_manager.get_project_status(project_id)
    except Exception as exc:
        raise_http_exception(exc)


@app.post("/tfpjts/{project_id}", response_model=ApplyResponse, status_code=202)
async def apply_project(project_id: str, payload: ApplyRequest) -> ApplyResponse:
    message = payload.message or "Terraform apply is in progress"
    try:
        with lock_manager.acquire(project_id, "apply_running", message):
            output = terraform_manager.run_apply(project_id, payload.variables)
        return ApplyResponse(project_id=project_id, action="apply", output=output)
    except Exception as exc:
        raise_http_exception(exc)


@app.delete("/tfpjts/{project_id}", response_model=DestroyResponse, status_code=202)
async def destroy_project(project_id: str, payload: DestroyRequest | None = None) -> DestroyResponse:
    payload = payload or DestroyRequest()
    message = payload.message or "Terraform destroy is in progress"
    try:
        with lock_manager.acquire(project_id, "destroy_running", message):
            output = terraform_manager.run_destroy(project_id, payload.variables)
        return DestroyResponse(project_id=project_id, action="destroy", output=output)
    except Exception as exc:
        raise_http_exception(exc)


@app.post("/tfpjts/{project_id}/git", response_model=GitCloneResponse, status_code=201)
async def clone_project(project_id: str, payload: GitCloneRequest) -> GitCloneResponse:
    message = "Git clone in progress"
    try:
        with lock_manager.acquire(project_id, "git_clone", message):
            terraform_manager.clone_project(project_id, payload.repo_url, payload.branch, payload.depth)
        status = terraform_manager.get_project_status(project_id)
        return GitCloneResponse(
            project_id=project_id,
            repo_url=payload.repo_url,
            branch=payload.branch,
            initialized=status.initialized,
        )
    except Exception as exc:
        raise_http_exception(exc)
