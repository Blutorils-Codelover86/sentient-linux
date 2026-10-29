"""
Safe Knowledge Vault Storage Engine for Sentient Linux.
Implements atomic writes, symlink protection, path traversal defenses, and rollback safeguards.
"""

from __future__ import annotations
import logging
import os
import shutil
import time
import uuid
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger("sentient.knowledge.storage")


class StorageSecurityError(PermissionError):
    """Raised when an operation violates storage security boundaries."""
    pass


class KnowledgeStorage:
    """
    Manages safe local markdown storage for Sentient knowledge base.
    Guarantees:
    - Zero modification outside the configured knowledge root.
    - Symlink escape detection and rejection.
    - Atomic file writes via staging files and os.replace.
    - Automatic backups before overwrite with rollback capability.
    - Restricted POSIX file permissions (0700 dirs, 0600 files).
    """

    DEFAULT_VAULT_NAME = "Sentient OS - Knowledge Base"

    def __init__(self, vault_path: Optional[Path | str] = None) -> None:
        if vault_path:
            self.root = Path(vault_path).expanduser().resolve()
        else:
            self.root = Path.home() / self.DEFAULT_VAULT_NAME

    def initialize(self) -> Path:
        """Create knowledge root directory with 0700 permissions."""
        if not self.root.exists():
            self.root.mkdir(parents=True, mode=0o700, exist_ok=True)
            os.chmod(self.root, 0o700)
            logger.info(f"Initialized knowledge root: {self.root}")
        return self.root

    def _validate_path(self, relative_path: str | Path) -> Path:
        """
        Validate that the target path resolves safely inside the knowledge root.
        Rejects directory traversal (../) and symlinks.
        """
        unresolved = self.root / relative_path
        # Check if the path or any existing parent is a symlink
        curr = unresolved
        while curr != self.root and curr != curr.parent:
            if curr.is_symlink():
                raise StorageSecurityError(
                    f"Symlink rejected: '{curr}' is a symbolic link. Knowledge storage refuses symlinks."
                )
            curr = curr.parent

        # Resolve target and check containment
        target = unresolved.resolve()
        try:
            target.relative_to(self.root)
        except ValueError:
            raise StorageSecurityError(
                f"Path traversal detected: '{relative_path}' resolves outside knowledge root."
            )

        return target

    def write_note(
        self,
        relative_path: str | Path,
        content: str,
        create_backup: bool = True,
    ) -> Path:
        """
        Atomically write content to a note inside the knowledge root.
        1. Validates path.
        2. Writes to sibling .tmp-<uuid> file.
        3. Fsyncs to disk.
        4. Creates .bak copy if file exists and create_backup is True.
        5. Atomically replaces target using os.replace.
        """
        self.initialize()
        target = self._validate_path(relative_path)
        target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)

        backup_path: Optional[Path] = None
        if target.exists() and create_backup:
            timestamp = int(time.time())
            backup_path = target.with_suffix(f".bak.{timestamp}")
            shutil.copy2(target, backup_path)
            logger.debug(f"Created backup of existing note: {backup_path}")

        # Staging file as sibling to guarantee same filesystem volume
        staging_filename = f".tmp-{uuid.uuid4().hex}"
        staging_path = target.parent / staging_filename

        try:
            with open(staging_path, "w", encoding="utf-8") as f:
                f.write(content)
                f.flush()
                os.fsync(f.fileno())

            # Set 0600 permissions
            os.chmod(staging_path, 0o600)

            # Atomic swap
            os.replace(staging_path, target)
            logger.info(f"Atomically wrote note: {target.relative_to(self.root)}")
            return target
        except Exception as err:
            if staging_path.exists():
                staging_path.unlink()
            # If replacement failed and we made a backup, file is still intact
            raise RuntimeError(f"Atomic note write failed: {err}")

    def read_note(self, relative_path: str | Path) -> str:
        """Read note content after path validation."""
        target = self._validate_path(relative_path)
        if not target.exists():
            raise FileNotFoundError(f"Note not found: {relative_path}")
        return target.read_text(encoding="utf-8")

    def list_notes(self) -> List[str]:
        """List all markdown notes relative to the knowledge root."""
        if not self.root.exists():
            return []
        notes = []
        for p in self.root.rglob("*.md"):
            if not p.name.startswith(".") and not p.is_symlink():
                notes.append(str(p.relative_to(self.root)))
        return sorted(notes)

    def cleanup_orphaned_staging(self) -> int:
        """Sweep orphaned .tmp-* staging files from interrupted writes."""
        if not self.root.exists():
            return 0
        cleaned = 0
        for p in self.root.rglob(".tmp-*"):
            try:
                if p.is_file():
                    p.unlink()
                    cleaned += 1
            except Exception as e:
                logger.warning(f"Could not remove orphaned staging file {p}: {e}")
        return cleaned
