"""
Unit tests for safe knowledge storage.
"""

from __future__ import annotations
import os
import stat
from pathlib import Path
import pytest

from sentient_linux.knowledge.storage import KnowledgeStorage, StorageSecurityError


def test_storage_atomic_write_and_read(tmp_path: Path):
    storage = KnowledgeStorage(vault_path=tmp_path / "vault")
    storage.initialize()

    # Check directory permissions are strictly 0700
    dir_mode = stat.S_IMODE(os.stat(storage.root).st_mode)
    assert dir_mode == 0o700

    note_path = storage.write_note("projects/sentient.md", "# Sentient Linux\nPort in progress.")
    assert note_path.exists()

    # Check file permissions are 0600
    file_mode = stat.S_IMODE(os.stat(note_path).st_mode)
    assert file_mode == 0o600

    content = storage.read_note("projects/sentient.md")
    assert "Port in progress" in content


def test_storage_backup_on_overwrite(tmp_path: Path):
    storage = KnowledgeStorage(vault_path=tmp_path / "vault")
    storage.initialize()

    storage.write_note("readme.md", "Version 1", create_backup=True)
    storage.write_note("readme.md", "Version 2", create_backup=True)

    content = storage.read_note("readme.md")
    assert content == "Version 2"

    # Verify backup exists
    backups = list(storage.root.glob("readme.bak.*"))
    assert len(backups) == 1
    assert backups[0].read_text() == "Version 1"


def test_storage_path_traversal_rejection(tmp_path: Path):
    storage = KnowledgeStorage(vault_path=tmp_path / "vault")
    storage.initialize()

    with pytest.raises(StorageSecurityError, match="Path traversal detected"):
        storage.write_note("../escape.md", "Malicious content")

    with pytest.raises(StorageSecurityError, match="Path traversal detected"):
        storage.read_note("../../etc/passwd")


def test_storage_symlink_rejection(tmp_path: Path):
    storage = KnowledgeStorage(vault_path=tmp_path / "vault")
    storage.initialize()

    outside_file = tmp_path / "outside.txt"
    outside_file.write_text("outside")

    # Create a symlink inside the vault pointing outside
    symlink_path = storage.root / "link_outside.md"
    symlink_path.symlink_to(outside_file)

    with pytest.raises(StorageSecurityError, match="Symlink rejected"):
        storage.read_note("link_outside.md")


def test_storage_cleanup_orphaned_staging(tmp_path: Path):
    storage = KnowledgeStorage(vault_path=tmp_path / "vault")
    storage.initialize()

    # Create dummy orphaned .tmp-* file
    orphan = storage.root / ".tmp-abcdef123456"
    orphan.write_text("incomplete write")

    cleaned = storage.cleanup_orphaned_staging()
    assert cleaned == 1
    assert not orphan.exists()
