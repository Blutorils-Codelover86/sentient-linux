"""
Knowledge Vault data model and indexing engine for Sentient Linux.
Direct translation of upstream VaultTree.swift:
- Scans on-disk Markdown vault (default: ~/Sentient OS - Knowledge Base/).
- Builds hierarchical folder/note tree (folders first, then notes, README pulled as pinned Overview).
- Title index: lowercased filename stem -> Path (resolves [[wikilinks]] and graph edges).
- Note reading: strips YAML frontmatter (---...---), promotes first '# H1' to title.
- Safe local storage with atomic writes, symlink rejection, and path traversal defense.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Set
from urllib.parse import unquote

from sentient_linux.knowledge.storage import KnowledgeStorage, StorageSecurityError

logger = logging.getLogger("sentient.knowledge.vault")


@dataclass
class VaultNode:
    """One node in the vault tree — a folder (with children) or a markdown note (a leaf)."""
    path: Path
    name: str                 # folder name, or the note's filename without ".md"
    is_folder: bool
    children: List[VaultNode] = field(default_factory=list)

    @property
    def id(self) -> str:
        return str(self.path)


class KnowledgeVault:
    """
    A loaded snapshot of the knowledge vault:
    - Root directory (defaults to ~/Sentient OS - Knowledge Base, or SENTIENT_VAULT_ROOT).
    - Hierarchical tree with README pulled out as pinned Overview.
    - Flat list of all notes (sorted alphabetically).
    - Title -> Path index for [[wikilink]] resolution.
    - Title & content search.
    """

    DEFAULT_VAULT_NAME = "Sentient OS - Knowledge Base"
    EXCLUDED_NAMES = {"writingstyle.md"}

    def __init__(
        self,
        root: Path,
        nodes: List[VaultNode],
        all_notes: List[VaultNode],
        title_index: Dict[str, Path],
        readme: Optional[Path] = None,
    ) -> None:
        self.root = root
        self.nodes = nodes
        self.all_notes = all_notes
        self.title_index = title_index
        self.readme = readme
        self.storage = KnowledgeStorage(self.root)

    @classmethod
    def get_default_vault_path(cls) -> Path:
        """Resolve vault root path (respects SENTIENT_VAULT_ROOT environment variable)."""
        override = os.environ.get("SENTIENT_VAULT_ROOT")
        if override:
            return Path(override).expanduser().resolve()
        return Path.home() / cls.DEFAULT_VAULT_NAME

    @classmethod
    def load(cls, custom_root: Optional[Path | str] = None) -> Optional[KnowledgeVault]:
        """
        Scan the vault folder into a browsable tree.
        Returns None if the vault folder does not exist yet.
        Cheap: only enumerates directory entries; note bodies are read lazily on selection.
        """
        if custom_root:
            root = Path(custom_root).expanduser().resolve()
        else:
            root = cls.get_default_vault_path()

        if not root.exists() or not root.is_dir():
            return None

        index: Dict[str, Path] = {}
        flat: List[VaultNode] = []

        def scan(dir_path: Path) -> List[VaultNode]:
            folders: List[VaultNode] = []
            notes: List[VaultNode] = []

            try:
                entries = list(dir_path.iterdir())
            except OSError as err:
                logger.warning(f"Error accessing directory {dir_path}: {err}")
                return []

            for entry in entries:
                name = entry.name
                if name.startswith("."):
                    continue   # Skip hidden files and dotfolders (.obsidian, .git)
                if name.lower() in cls.EXCLUDED_NAMES:
                    continue   # Skip internal writingstyle.md

                # Security check: skip symlinks
                if entry.is_symlink():
                    logger.warning(f"Skipping symlink in vault: {entry}")
                    continue

                if entry.is_dir():
                    sub_children = scan(entry)
                    folders.append(VaultNode(
                        path=entry,
                        name=name,
                        is_folder=True,
                        children=sub_children,
                    ))
                elif entry.is_file() and entry.suffix.lower() == ".md":
                    stem = entry.stem
                    index[stem.lower()] = entry
                    node = VaultNode(
                        path=entry,
                        name=stem,
                        is_folder=False,
                        children=[],
                    )
                    notes.append(node)
                    flat.append(node)

            folders.sort(key=lambda x: x.name.lower())
            notes.sort(key=lambda x: x.name.lower())
            # Folders first, then notes — Finder / Obsidian parity
            return folders + notes

        top_nodes = scan(root)

        # Pull out README (case-insensitive) as pinned Overview
        readme_path: Optional[Path] = None
        filtered_top: List[VaultNode] = []
        for n in top_nodes:
            if not n.is_folder and n.name.lower() == "readme":
                readme_path = n.path
            else:
                filtered_top.append(n)

        flat.sort(key=lambda x: x.name.lower())

        return cls(
            root=root,
            nodes=filtered_top,
            all_notes=flat,
            title_index=index,
            readme=readme_path,
        )

    def resolve(self, wikilink: str) -> Optional[Path]:
        """
        Resolve a [[wikilink]] target to a note Path if one exists.
        Supports:
        - [[Title]] -> "title"
        - [[Title|Alias]] -> "title"
        - [[Title#Heading]] -> "title"
        """
        clean = wikilink.strip()
        if not clean:
            return None

        # Strip heading fragment
        if "#" in clean:
            clean = clean.split("#", 1)[0].strip()

        # Strip alias
        if "|" in clean:
            clean = clean.split("|", 1)[0].strip()

        return self.title_index.get(clean.lower())

    def ancestors(self, note_path: Path) -> List[Path]:
        """
        The folder Paths from the vault root down to (but excluding) note_path,
        so the sidebar tree can automatically expand to reveal a jumped note.
        """
        result: List[Path] = []
        curr = note_path.parent
        root_resolved = self.root.resolve()
        while curr != root_resolved and root_resolved in curr.parents:
            result.append(curr)
            curr = curr.parent
        return result

    @staticmethod
    def read(path: Path) -> Tuple[str, str]:
        """
        Read note content for display:
        - Strips leading YAML frontmatter (---...---).
        - Promotes first '# H1' line to note title.
        - Returns (title, markdown_body).
        """
        if not path.exists():
            return (path.stem, f"Note not found: `{path.name}`")

        try:
            raw = path.read_text(encoding="utf-8")
        except Exception as err:
            return (path.stem, f"Error reading note: {err}")

        text = raw
        # Strip frontmatter
        if text.startswith("---"):
            lines = text.split("\n")
            close_idx = -1
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    close_idx = i
                    break
            if close_idx != -1:
                text = "\n".join(lines[close_idx + 1:])

        text = text.strip()
        lines = text.split("\n")

        title = path.stem
        body_lines = lines

        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            body_lines = lines[1:]

        body = "\n".join(body_lines).strip()
        return (title, body)

    def search(self, query: str) -> List[VaultNode]:
        """
        Search indexed note titles and content.
        Does NOT touch any files outside the vault root.
        """
        q = query.strip().lower()
        if not q:
            return []

        results: List[VaultNode] = []
        for node in self.all_notes:
            # Match in note filename / stem
            if q in node.name.lower():
                results.append(node)
                continue

            # Match in note title or content
            try:
                title, body = self.read(node.path)
                if q in title.lower() or q in body.lower():
                    results.append(node)
            except Exception:
                continue

        return results

    def create_note(self, dir_path: Optional[Path], name: str) -> Path:
        """Create a new note seeded with '# {title}\\n\\n' atomically."""
        target_dir = dir_path or self.root
        clean_name = self._sanitize_name(name, fallback="Untitled")
        target_path = self._unique_path(target_dir, clean_name, ext=".md")

        title = target_path.stem
        initial_content = f"# {title}\n\n"

        rel_path = target_path.relative_to(self.root)
        self.storage.write_note(rel_path, initial_content, create_backup=False)
        return target_path

    def create_folder(self, dir_path: Optional[Path], name: str) -> Path:
        """Create a new subfolder inside the vault."""
        target_dir = dir_path or self.root
        clean_name = self._sanitize_name(name, fallback="New Folder")
        target_path = self._unique_path(target_dir, clean_name, ext=None)

        # Validate security
        validated = self.storage._validate_path(target_path.relative_to(self.root))
        validated.mkdir(parents=True, mode=0o700, exist_ok=True)
        return validated

    def delete_item(self, path: Path) -> bool:
        """
        Move note or folder to trash.
        Returns False if the target is the root README.
        """
        if self.readme and path.resolve() == self.readme.resolve():
            logger.warning("Attempted to delete vault README Overview; ignored.")
            return False

        # Validate security before deletion
        rel_path = path.resolve().relative_to(self.root.resolve())
        _ = self.storage._validate_path(rel_path)

        # Use Gio.File.trash if available
        try:
            import gi
            gi.require_version("Gio", "2.0")
            from gi.repository import Gio
            gfile = Gio.File.new_for_path(str(path))
            return bool(gfile.trash(None))
        except Exception as err:
            logger.warning(f"Gio trash failed ({err}), unlinking directly: {path}")
            if path.is_dir():
                import shutil
                shutil.rmtree(path)
            else:
                path.unlink()
            return True

    @staticmethod
    def _sanitize_name(raw: str, fallback: str) -> str:
        s = raw.replace("/", "-").replace(":", "-").strip()
        return s[:120] if s else fallback

    @staticmethod
    def _unique_path(dir_path: Path, name: str, ext: Optional[str]) -> Path:
        def make_path(base_name: str) -> Path:
            if ext:
                return dir_path / f"{base_name}{ext}"
            return dir_path / base_name

        cand = make_path(name)
        i = 2
        while cand.exists():
            cand = make_path(f"{name} {i}")
            i += 1
        return cand
