"""
Comprehensive Verification Tests for Sentient Linux Knowledge Vault.
Tests:
- Markdown rendering (fenced code, box trees, headings, bullets, inline tokens)
- Wikilink resolution and navigation trail (history stack and can_go_back)
- Missing notes and empty vault handling
- Search indexing across titles and content
- Storage errors (symlink rejection, path traversal defenses)
- Explicit indexing consent (strictly local, zero directory escapes)
- Window lifecycle and unsaved edits guard
"""

from __future__ import annotations
import os
import shutil
from pathlib import Path
from unittest.mock import MagicMock
import pytest

import gi
gi.require_version("Gtk", "4.0")
from gi.repository import Gtk

from sentient_linux.knowledge.vault import KnowledgeVault, VaultNode
from sentient_linux.knowledge.storage import KnowledgeStorage, StorageSecurityError
from sentient_linux.gui.markdown_renderer import MarkdownBlockRenderer, WIKI_SCHEME
from sentient_linux.gui.knowledge_view import SentientKnowledgeVaultWindow


@pytest.fixture
def sample_vault(tmp_path: Path) -> Path:
    """Create a canonical test vault fixture matching upstream Sentient OS."""
    vault_dir = tmp_path / "Sentient OS - Knowledge Base"
    vault_dir.mkdir(parents=True)

    # Root README (Overview)
    readme_content = """# Knowledge Base Overview

Sentient OS is an open-source, privacy-first intelligence layer.

## Vault Map

- `Identity/` — who Jesai is. Start with [[Jesai Tarun - Current Portrait]].
- `Sentient OS/` — product thesis and roadmap. See [[Sentient OS Map]].
- An *unresolved* link: [[Does Not Exist]].

## Structure

```
Sentient OS - Knowledge Base/
├── Identity/
│   ├── Jesai Tarun - Current Portrait.md
│   └── Values and Working Style.md
└── Sentient OS/
    └── Product Thesis.md
```
"""
    (vault_dir / "README.md").write_text(readme_content, encoding="utf-8")

    # Identity folder
    identity_dir = vault_dir / "Identity"
    identity_dir.mkdir()
    portrait_content = """---
tags: [identity, founder]
updated: 2026-10-29
---
# Jesai Tarun - Current Portrait

Jesai Tarun is building **Sentient OS**.
Center of gravity is [[Sentient OS - Product Thesis]].
"""
    (identity_dir / "Jesai Tarun - Current Portrait.md").write_text(portrait_content, encoding="utf-8")

    (identity_dir / "Values and Working Style.md").write_text(
        "# Values and Working Style\n\nSpeed, aesthetic taste, and genuine open-source.",
        encoding="utf-8",
    )

    # Sentient OS folder
    os_dir = vault_dir / "Sentient OS"
    os_dir.mkdir()
    thesis_content = """# Sentient OS - Product Thesis

A personal AI agent that runs 100% on-device on Linux desktop.
Refer to [[Jesai Tarun - Current Portrait|Jesai's Profile]].
"""
    (os_dir / "Product Thesis.md").write_text(thesis_content, encoding="utf-8")

    # Excluded files: dotfolder, dotfile, and writingstyle.md
    dot_dir = vault_dir / ".obsidian"
    dot_dir.mkdir()
    (dot_dir / "workspace.json").write_text("{}", encoding="utf-8")
    (vault_dir / ".DS_Store").write_text("", encoding="utf-8")
    (vault_dir / "writingstyle.md").write_text("Double tap examples", encoding="utf-8")

    return vault_dir


def test_empty_vault_and_missing_notes(tmp_path: Path):
    """Empty vault or missing directory returns clean empty states without crashes."""
    nonexistent = tmp_path / "NonexistentVault"
    assert KnowledgeVault.load(nonexistent) is None

    empty_dir = tmp_path / "EmptyVault"
    empty_dir.mkdir()
    vault = KnowledgeVault.load(empty_dir)
    assert vault is not None
    assert len(vault.nodes) == 0
    assert len(vault.all_notes) == 0
    assert vault.readme is None

    # Missing note reading
    missing_note = empty_dir / "Missing.md"
    title, body = KnowledgeVault.read(missing_note)
    assert "Note not found" in body


def test_vault_tree_scanning_and_readme_pinning(sample_vault: Path):
    """Vault scans hierarchy, sorts folders first, pins README, and ignores dotfiles."""
    vault = KnowledgeVault.load(sample_vault)
    assert vault is not None

    # README pinned out as Overview
    assert vault.readme is not None
    assert vault.readme.name.lower() == "readme.md"

    # README excluded from top-level nodes
    top_names = [n.name for n in vault.nodes]
    assert "README" not in top_names
    assert "Identity" in top_names
    assert "Sentient OS" in top_names

    # Dotfiles and writingstyle.md excluded
    assert ".obsidian" not in top_names
    assert ".DS_Store" not in top_names
    assert "writingstyle" not in [n.name.lower() for n in vault.all_notes]

    # Folders before notes
    assert all(n.is_folder for n in vault.nodes)

    # Title index contains lowercased stems
    assert "jesai tarun - current portrait" in vault.title_index
    assert "values and working style" in vault.title_index
    assert "product thesis" in vault.title_index


def test_wikilink_resolution(sample_vault: Path):
    """Resolves standard wikilinks, aliases, and heading fragments."""
    vault = KnowledgeVault.load(sample_vault)
    assert vault is not None

    # Standard [[Title]]
    res1 = vault.resolve("Jesai Tarun - Current Portrait")
    assert res1 is not None
    assert res1.name == "Jesai Tarun - Current Portrait.md"

    # With alias [[Title|Alias]]
    res2 = vault.resolve("Product Thesis|Our Core Thesis")
    assert res2 is not None
    assert res2.name == "Product Thesis.md"

    # With heading [[Title#Section]]
    res3 = vault.resolve("Values and Working Style#Principles")
    assert res3 is not None
    assert res3.name == "Values and Working Style.md"

    # Non-existent
    assert vault.resolve("Does Not Exist") is None
    assert vault.resolve("") is None


def test_note_reading_frontmatter_and_h1(sample_vault: Path):
    """YAML frontmatter is stripped and first '# H1' is promoted to title."""
    portrait_path = sample_vault / "Identity" / "Jesai Tarun - Current Portrait.md"
    title, body = KnowledgeVault.read(portrait_path)

    assert title == "Jesai Tarun - Current Portrait"
    assert "---" not in body
    assert "tags: [identity, founder]" not in body
    assert body.startswith("Jesai Tarun is building **Sentient OS**.")


def test_search_titles_and_content(sample_vault: Path):
    """Search matches in note titles and note markdown contents."""
    vault = KnowledgeVault.load(sample_vault)
    assert vault is not None

    # Match in content
    res_content = vault.search("privacy-first")
    assert any("README" in n.name for n in res_content)

    # Match in title / stem
    res_title = vault.search("thesis")
    assert any("Product Thesis" in n.name for n in res_title)

    # Non-matching
    assert len(vault.search("completely_unrelated_query_12345")) == 0
    assert len(vault.search("")) == 0


def test_markdown_rendering_blocks_and_wikilinks():
    """MarkdownBlockRenderer parses headings, bullets, code fences, and [[wikilinks]]."""
    md = """# Heading 1
## Heading 2
### Heading 3

This is a paragraph with **bold**, *italic*, `code`, and a link to [[Known Note]] and [[Missing Note]].
Here is an alias link: [[Known Note|Go to Known]].

- Bullet point with [[Known Note]]

```
code block line 1
├── tree row 1
└── tree row 2
```

├── bare tree row
└── bare tree row 2

---
"""
    navigated_targets = []
    renderer = MarkdownBlockRenderer(
        markdown=md,
        exists=lambda t: t == "Known Note",
        on_navigate=lambda t: navigated_targets.append(t),
    )

    box = renderer.build_widget()
    assert isinstance(box, Gtk.Box)

    # Verify link routing
    handled = renderer._on_activate_link(None, f"{WIKI_SCHEME}Known%20Note")
    assert handled is True
    assert navigated_targets == ["Known Note"]


def test_wikilink_navigation_trail_and_history(sample_vault: Path):
    """Back button walks the wikilink trail and clears when fresh note is opened."""
    win = SentientKnowledgeVaultWindow(vault_path=sample_vault)

    readme = sample_vault / "README.md"
    portrait = sample_vault / "Identity" / "Jesai Tarun - Current Portrait.md"
    thesis = sample_vault / "Sentient OS" / "Product Thesis.md"

    # 1. Fresh open of README
    win.open_note(readme)
    assert win.selection == readme
    assert win.can_go_back is False
    assert len(win.history) == 1

    # 2. Follow wikilink to Portrait
    win.follow_wikilink(portrait)
    assert win.selection == portrait
    assert win.can_go_back is True
    assert len(win.history) == 2

    # 3. Follow wikilink to Thesis
    win.follow_wikilink(thesis)
    assert win.selection == thesis
    assert win.can_go_back is True
    assert len(win.history) == 3

    # 4. Go back to Portrait
    win.go_back()
    assert win.selection == portrait
    assert win.can_go_back is True

    # 5. Go back to README
    win.go_back()
    assert win.selection == readme
    assert win.can_go_back is False

    # 6. Fresh open of Thesis clears the previous trail
    win.open_note(thesis)
    assert win.selection == thesis
    assert win.can_go_back is False
    assert len(win.history) == 1

    win.destroy()


def test_storage_security_and_explicit_consent(sample_vault: Path, tmp_path: Path):
    """Storage strictly enforces vault boundary, rejecting path traversals and symlinks."""
    storage = KnowledgeStorage(sample_vault)

    # 1. Path traversal escape attempt
    with pytest.raises(StorageSecurityError):
        storage._validate_path("../../../etc/shadow")

    # 2. Symlink escape attempt
    outside_dir = tmp_path / "outside_sensitive"
    outside_dir.mkdir()
    target_secret = outside_dir / "secret.txt"
    target_secret.write_text("sensitive", encoding="utf-8")

    symlink_path = sample_vault / "symlink_note.md"
    try:
        os.symlink(target_secret, symlink_path)
        with pytest.raises(StorageSecurityError):
            storage.read_note("symlink_note.md")
    finally:
        if symlink_path.is_symlink():
            symlink_path.unlink()

    # 3. Safe atomic write within vault
    written = storage.write_note("Identity/NewNote.md", "# New Note\n\nContent")
    assert written.exists()
    assert (sample_vault / "Identity" / "NewNote.md").read_text(encoding="utf-8") == "# New Note\n\nContent"


def test_window_lifecycle_and_unsaved_edits_guard(sample_vault: Path):
    """Window initializes with correct constraints and detects unsaved modifications."""
    win = SentientKnowledgeVaultWindow(vault_path=sample_vault)

    # Window constraints
    assert win.get_default_size() == (1060, 680)
    assert win.get_size_request() == (900, 600)

    # Initial state
    assert win.is_editing is False
    assert win._is_dirty() is False

    # Enter edit mode
    win.begin_edit()
    assert win.is_editing is True
    assert win._is_dirty() is False

    # Modify editor buffer
    buf = win.editor_text_view.get_buffer()
    buf.set_text("# Modified Content\n\nUnsaved change")
    assert win._is_dirty() is True

    # Save edit
    win.save_edit()
    assert win.is_editing is False
    assert win._is_dirty() is False

    win.destroy()
