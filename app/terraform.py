from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Iterable

from .config import Settings
from .exceptions import ProjectNotFoundError, TerraformError
from .locks import LockManager
from .schemas import LockInfo, ProjectStatus


class TerraformManager:
    def __init__(self, settings: Settings, lock_manager: LockManager) -> None:
        self.settings = settings
        self.lock_manager = lock_manager

    def _project_path(self, project_id: str) -> Path:
        if not project_id or project_id.startswith(".") or "/" in project_id:
            raise ProjectNotFoundError(project_id)
        path = self.settings.terraform_root / project_id
        if not path.exists() or not path.is_dir():
            raise ProjectNotFoundError(project_id)
        return path

    def list_projects(self) -> list[ProjectStatus]:
        projects: list[ProjectStatus] = []
        for path in sorted(self.settings.terraform_root.iterdir()):
            if not path.is_dir():
                continue
            project_id = path.name
            projects.append(self.get_project_status(project_id))
        return projects

    def initialize_projects(self) -> None:
        terraform_bin = shutil.which(self.settings.terraform_bin)
        if terraform_bin is None:
            raise FileNotFoundError(f"Terraform binary '{self.settings.terraform_bin}' not found")

        for path in sorted(self.settings.terraform_root.iterdir()):
            if not path.is_dir():
                continue
            self._terraform_init(path)

    def _terraform_init(self, path: Path) -> None:
        if (path / ".terraform").exists():
            return
        self._run_cmd(["init", "-input=false"], path)

    def _build_var_args(self, variables: dict[str, str]) -> list[str]:
        args: list[str] = []
        for key, value in variables.items():
            args.extend(["-var", f"{key}={value}"])
        return args

    def _run_cmd(self, args: Iterable[str], project_path: Path) -> str:
        cmd = [self.settings.terraform_bin, *list(args)]
        process = subprocess.run(
            cmd,
            cwd=project_path,
            check=False,
            capture_output=True,
            text=True,
        )
        output = process.stdout + "\n" + process.stderr
        if process.returncode != 0:
            raise TerraformError(
                f"Terraform command failed ({' '.join(cmd)})",
                output=output,
            )
        return output.strip()

    def run_apply(self, project_id: str, variables: dict[str, str]) -> str:
        project_path = self._project_path(project_id)
        self._terraform_init(project_path)
        args = ["apply", "-auto-approve", "-no-color", *self._build_var_args(variables)]
        return self._run_cmd(args, project_path)

    def run_destroy(self, project_id: str, variables: dict[str, str]) -> str:
        project_path = self._project_path(project_id)
        self._terraform_init(project_path)
        args = ["destroy", "-auto-approve", *self._build_var_args(variables)]
        return self._run_cmd(args, project_path)

    def get_project_status(self, project_id: str) -> ProjectStatus:
        project_path = self._project_check_or_placeholder(project_id)
        initialized = (project_path / ".terraform").exists()
        has_state = (project_path / "terraform.tfstate").exists()
        lock_info = self.lock_manager.get_lock(project_id)
        return ProjectStatus(
            id=project_id,
            path=str(project_path),
            initialized=initialized,
            has_state=has_state,
            lock_info=lock_info,
        )

    def _project_check_or_placeholder(self, project_id: str) -> Path:
        path = self.settings.terraform_root / project_id
        if not path.exists():
            raise ProjectNotFoundError(project_id)
        return path

    def clone_project(self, project_id: str, repo_url: str, branch: str | None, depth: int | None) -> None:
        project_path = self.settings.terraform_root / project_id
        if project_path.exists():
            raise TerraformError(f"Project directory '{project_id}' already exists")

        clone_cmd = ["git", "clone"]
        if depth or self.settings.git_clone_depth:
            clone_cmd.extend(["--depth", str(depth or self.settings.git_clone_depth)])
        if branch:
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([repo_url, str(project_path)])

        process = subprocess.run(
            clone_cmd,
            cwd=self.settings.terraform_root,
            check=False,
            capture_output=True,
            text=True,
        )
        if process.returncode != 0:
            raise TerraformError(
                f"Git clone failed for project '{project_id}'",
                output=process.stdout + "\n" + process.stderr,
            )
        self._terraform_init(project_path)

