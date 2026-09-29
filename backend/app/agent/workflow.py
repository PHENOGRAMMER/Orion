"""
Controlled edit workflow for Orion's production-v1 agent.

The model should produce proposed edits, but this module owns the dangerous
parts: path checks, diff creation, application, validation, and persistence.
"""

from __future__ import annotations

import difflib
import subprocess
import sys
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal


from app.core.persistence import OrionPersistence


ProposalStatus = Literal["proposed", "applying", "applied", "failed"]
ValidationMode = Literal["backend-tests", "pytest", "none"]
# Serialize proposal application within this Python process.
# Cross-process coordination should remain a persistence-layer concern.
_apply_lock = threading.RLock()


class AgentWorkflowError(ValueError):
    """Raised when an edit proposal cannot be created or applied safely."""


@dataclass(frozen=True)
class TextEdit:
    path: str
    find: str
    replace: str


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise AgentWorkflowError(f"File is not UTF-8 text: {path}") from exc


def _resolve_file(project_root: Path, relative_path: str) -> Path:
    root = project_root.resolve()
    target = (root / relative_path).resolve()

    if target == root or not target.is_relative_to(root):
        raise AgentWorkflowError(f"Edit path is outside the project root: {relative_path}")

    if not target.exists():
        raise AgentWorkflowError(f"Edit target does not exist: {relative_path}")

    if not target.is_file():
        raise AgentWorkflowError(f"Edit target is not a file: {relative_path}")

    return target


def _diff(relative_path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )


def _apply_text_edits(project_root: Path, edits: list[TextEdit]) -> list[dict[str, Any]]:
    files: dict[str, tuple[Path, str, str]] = {}

    for edit in edits:
        target = _resolve_file(project_root, edit.path)
        if edit.path in files:
            _target, original, current = files[edit.path]
        else:
            original = _read_text(target)
            current = original

        count = current.count(edit.find)
        if count != 1:
            raise AgentWorkflowError(
                f"Expected exactly one match in {edit.path}, found {count}."
            )

        after = current.replace(edit.find, edit.replace, 1)
        files[edit.path] = (target, original, after)

    changes: list[dict[str, Any]] = []
    for relative_path, (_target, before, after) in files.items():
        changes.append(
            {
                "path": relative_path,
                "before": before,
                "after": after,
                "diff": _diff(relative_path, before, after),
            }
        )

    return changes


def _validation_command(
    project_root: Path,
    mode: ValidationMode,
    test_paths: list[str] | None = None,
) -> tuple[list[str] | None, Path]:
    if mode == "none":
        return None, project_root

    if mode == "backend-tests":
        backend = project_root / "backend"
        cwd = backend if backend.exists() else project_root
        return [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"], cwd

    if mode == "pytest":
        backend = project_root / "backend"
        cwd = backend if backend.exists() else project_root
        cmd = [sys.executable, "-m", "pytest", "-v"]
        if test_paths:
            cmd.extend(test_paths)
        return cmd, cwd

    raise AgentWorkflowError(f"Unsupported validation mode: {mode}")


def _run_validation(
    project_root: Path,
    mode: ValidationMode,
    test_paths: list[str] | None = None,
) -> dict[str, Any]:
    command, cwd = _validation_command(project_root, mode, test_paths)
    if command is None:
        return {
            "mode": mode,
            "passed": False,
            "validated": False,
            "command": None,
            "returncode": None,
            "output": "Validation skipped; changes were not validated.",
        }

    kwargs: dict[str, Any] = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    completed = subprocess.run(
        command,
        cwd=str(cwd),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=120,
        check=False,
        **kwargs,
    )

    return {
        "mode": mode,
        "passed": completed.returncode == 0,
        "validated": True,
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "output": completed.stdout[-8000:],
    }


class EditProposal(dict):
    """
    Dict subclass supporting both dictionary key lookup (`proposal["status"]`)
    and attribute lookup (`proposal.status`).
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.__dict__ = self

    @property
    def id(self) -> str:
        return self.get("proposal_id", "")

    @id.setter
    def id(self, value: str) -> None:
        self["proposal_id"] = value

    def to_dict(self) -> dict[str, Any]:
        return dict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EditProposal:
        return cls(data)


class AgentWorkflow:
    def __init__(self, store: OrionPersistence | None = None) -> None:
        self.store = store
        self._proposals: dict[str, EditProposal] = {}

    def _audit(
        self,
        *,
        action: str,
        status: str,
        proposal: EditProposal | dict[str, Any],
        actor: Any | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """Best-effort durable audit logging."""
        if self.store is None:
            return

        prop_dict = proposal.to_dict() if isinstance(proposal, EditProposal) else proposal

        try:
            self.store.record_audit_event(
                event_id=uuid.uuid4().hex,
                action=action,
                status=status,
                actor_key_id=getattr(actor, "key_id", None),
                actor_name=getattr(actor, "name", None),
                actor_role=getattr(actor, "role", None),
                resource_type="edit_proposal",
                resource_id=prop_dict.get("proposal_id"),
                project_path=prop_dict.get("project_path"),
                details=details,
            )
        except Exception as exc:
            print(f"[Orion] Audit logging failed: {type(exc).__name__}: {exc}")

    def create_proposal(
        self,
        *,
        project_root: Path,
        objective: str = "",
        edits: list[TextEdit] | None = None,
        changes: list[dict[str, Any]] | None = None,
        rationale: str = "",
        validation: ValidationMode = "backend-tests",
        test_paths: list[str] | None = None,
        allow_test_modes: bool = False,
        actor: Any | None = None,
    ) -> EditProposal:
        if validation == "none" and not allow_test_modes:
            raise AgentWorkflowError("Validation mode 'none' is restricted to internal evaluation tests.")

        obj = (objective or rationale).strip()

        if edits:
            formatted_changes = _apply_text_edits(project_root, edits)
        elif changes:
            formatted_changes = []
            for ch in changes:
                path_str = ch["path"]
                old_c = ch.get("old_content", ch.get("before", ""))
                new_c = ch.get("new_content", ch.get("after", ""))
                formatted_changes.append(
                    {
                        "path": path_str,
                        "before": old_c,
                        "after": new_c,
                        "diff": _diff(path_str, old_c, new_c),
                    }
                )
        else:
            raise AgentWorkflowError("At least one edit or change is required.")

        pid = uuid.uuid4().hex[:12]
        proposal = EditProposal(
            proposal_id=pid,
            project_path=str(project_root.resolve()),
            objective=obj,
            status="proposed",
            validation_mode=validation,
            test_paths=test_paths or [],
            changes=formatted_changes,
            diff="\n".join(change["diff"] for change in formatted_changes),
            summary=f"Prepared {len(formatted_changes)} file change(s).",
            validation=None,
        )

        self._proposals[pid] = proposal

        if self.store is not None:
            self.store.save_edit_proposal(proposal.to_dict())

        self._audit(
            action="proposal.created",
            status="success",
            proposal=proposal,
            actor=actor,
            details={
                "files_changed": len(formatted_changes),
                "validation_mode": validation,
            },
        )

        return proposal

    def load_proposal(self, proposal_id: str) -> EditProposal | None:
        if proposal_id in self._proposals:
            return self._proposals[proposal_id]
        if self.store is None:
            return None
        data = self.store.load_edit_proposal(proposal_id)
        if data:
            prop = EditProposal.from_dict(data)
            self._proposals[proposal_id] = prop
            return prop
        return None

    def apply_proposal(
        self,
        proposal_id: str,
        *,
        project_root: Path | None = None,
        approved: bool = True,
        validation_mode: ValidationMode | None = None,
        actor: Any | None = None,
    ) -> EditProposal:
        if not approved:
            raise AgentWorkflowError("Proposal application was not approved.")

        proposal = self.load_proposal(proposal_id)
        if proposal is None:
            raise AgentWorkflowError(f"Unknown proposal: {proposal_id}")

        if proposal["status"] != "proposed":
            raise AgentWorkflowError(f"Proposal is already {proposal['status']}.")

        persisted_validation_mode = proposal.get(
            "validation_mode",
            "backend-tests",
        )

        if validation_mode is not None and validation_mode != persisted_validation_mode:
            raise AgentWorkflowError(
                "Validation mode cannot be changed after proposal creation."
            )

        proposal_root = Path(proposal["project_path"]).resolve()

        if project_root is not None:
            supplied_root = project_root.resolve()

            if supplied_root != proposal_root:
                raise AgentWorkflowError(
                    "Proposal belongs to a different project root."
                )

        root = proposal_root

        with _apply_lock:
            if self.store is not None:
                claimed = self.store.transition_edit_proposal_status(
                    proposal_id,
                    expected_status="proposed",
                    new_status="applying",
                )
                if not claimed:
                    raise AgentWorkflowError(
                        "Proposal is already being applied or is no longer available."
                    )

            proposal["status"] = "applying"

            try:
                original_contents: dict[Path, str] = {}

                for change in proposal["changes"]:
                    target = _resolve_file(root, change["path"])
                    current = _read_text(target)

                    if current != change["before"]:
                        raise AgentWorkflowError(
                            f"File changed since proposal was created: {change['path']}"
                        )

                    original_contents[target] = current

                for change in proposal["changes"]:
                    target = _resolve_file(root, change["path"])
                    target.write_text(change["after"], encoding="utf-8")

                validation = _run_validation(
                    root,
                    persisted_validation_mode,
                    proposal.get("test_paths") or None,
                )
                if persisted_validation_mode == "none":
                    validation["passed"] = True

                proposal["validation"] = validation

                if validation["passed"]:
                    if self.store is not None:
                        transitioned = self.store.transition_edit_proposal_status(
                            proposal_id,
                            expected_status="applying",
                            new_status="applied",
                        )
                        if not transitioned:
                            raise AgentWorkflowError(
                                "Proposal state changed unexpectedly during apply."
                            )

                    proposal["status"] = "applied"
                    proposal["summary"] = (
                        "Applied changes and validation passed."
                    )
                    self._audit(
                        action="proposal.applied",
                        status="success",
                        proposal=proposal,
                        actor=actor,
                        details={
                            "files_changed": len(proposal["changes"]),
                            "validation": validation,
                        },
                    )
                else:
                    for target, original in original_contents.items():
                        target.write_text(original, encoding="utf-8")

                    if self.store is not None:
                        transitioned = self.store.transition_edit_proposal_status(
                            proposal_id,
                            expected_status="applying",
                            new_status="failed",
                        )
                        if not transitioned:
                            raise AgentWorkflowError(
                                "Proposal state changed unexpectedly during rollback."
                            )

                    proposal["status"] = "failed"
                    proposal["summary"] = (
                        "Validation failed; all changes were rolled back."
                    )
                    self._audit(
                        action="proposal.failed",
                        status="failed",
                        proposal=proposal,
                        actor=actor,
                        details={
                            "reason": "validation_failed",
                            "files_changed": len(proposal["changes"]),
                            "validation": validation,
                            "rolled_back": True,
                        },
                    )

            except Exception as exc:
                rollback_succeeded = True

                if "original_contents" in locals():
                    for target, original in original_contents.items():
                        try:
                            target.write_text(original, encoding="utf-8")
                        except Exception:
                            rollback_succeeded = False

                proposal["status"] = "failed"
                proposal["validation"] = {
                    "mode": proposal.get("validation_mode"),
                    "passed": False,
                    "command": None,
                    "returncode": None,
                    "output": f"{type(exc).__name__}: {exc}",
                }
                proposal["summary"] = "Failed to apply proposal."

                self._audit(
                    action="proposal.failed",
                    status="failed",
                    proposal=proposal,
                    actor=actor,
                    details={
                        "reason": "exception",
                        "error_type": type(exc).__name__,
                        "rolled_back": rollback_succeeded,
                        "rollback_succeeded": rollback_succeeded,
                    },
                )

                if self.store is not None:
                    self.store.save_edit_proposal(proposal.to_dict())

                raise

        if self.store is not None:
            self.store.save_edit_proposal(proposal.to_dict())

        return proposal


_default_workflow = AgentWorkflow()


def create_proposal(
    project_root: Path,
    changes: list[dict[str, Any]] | None = None,
    rationale: str = "",
    objective: str = "",
    edits: list[TextEdit] | None = None,
    validation: ValidationMode = "backend-tests",
    allow_test_modes: bool = False,
    actor: Any | None = None,
) -> EditProposal:
    return _default_workflow.create_proposal(
        project_root=project_root,
        objective=objective or rationale,
        edits=edits,
        changes=changes,
        rationale=rationale,
        validation=validation,
        allow_test_modes=allow_test_modes,
        actor=actor,
    )


def apply_proposal(
    project_root: Path | None = None,
    proposal_id: str = "",
    approved: bool = True,
    validation_mode: ValidationMode | None = None,
    actor: Any | None = None,
) -> EditProposal:
    return _default_workflow.apply_proposal(
        proposal_id=proposal_id,
        project_root=project_root,
        approved=approved,
        validation_mode=validation_mode,
        actor=actor,
    )
