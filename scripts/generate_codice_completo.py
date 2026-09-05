"""Generate codice_completo.md with project tree + main source contents."""

from __future__ import annotations

from pathlib import Path

root = Path(__file__).resolve().parents[1]
out = root / "codice_completo.md"

skip_dirs = {
    ".venv",
    "venv",
    "node_modules",
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".cursor",
    "data",
    "models",
    "results",
    "tmp_cal_test",
    ".tools",
    "htmlcov",
    ".eggs",
    "dist",
    "build",
    "agent-transcripts",
    "photos",
    "profiles",
    "profiles_deleted",
}
skip_names = {
    ".env",
    "messaging.json",
    "codice_completo.md",
    "APRI_SPOTIFY.html",
    "METTI_CHIAVI_RENDER.html",
    ".DS_Store",
    "Thumbs.db",
}
src_ext = {".py", ".html", ".js", ".css"}
include_roots = [root / "src", root / "scripts", root / "tests"]


def is_skipped_rel(rel: Path) -> bool:
    return any(part in skip_dirs for part in rel.parts)


tree_lines: list[str] = []


def walk_tree(dir_path: Path, prefix: str = "") -> None:
    try:
        entries = sorted(dir_path.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower()))
    except PermissionError:
        return
    filtered: list[Path] = []
    for entry in entries:
        if entry.name in skip_dirs or entry.name in skip_names:
            continue
        if entry.name.startswith(".") and entry.name != ".env.example":
            continue
        filtered.append(entry)
    for index, entry in enumerate(filtered):
        last = index == len(filtered) - 1
        branch = "└── " if last else "├── "
        tree_lines.append(prefix + branch + entry.name + ("/" if entry.is_dir() else ""))
        if entry.is_dir() and entry.name not in skip_dirs:
            walk_tree(entry, prefix + ("    " if last else "│   "))


walk_tree(root)

files: list[Path] = []
for base in include_roots:
    if not base.exists():
        continue
    for path in sorted(base.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if is_skipped_rel(rel):
            continue
        if path.name in skip_names or path.suffix.lower() not in src_ext:
            continue
        files.append(path)

parts: list[str] = []
parts.append("# Codice completo — Iris Nous\n\n")
parts.append(
    "Questo file raccoglie l'albero del progetto e il contenuto dei file sorgente "
    "principali (Python, HTML, CSS, JavaScript). Esclusi: `.venv`, `node_modules`, "
    "`.git`, `data/`, cache, segreti (`.env`, `messaging.json`) e tool HTML di supporto.\n\n"
)
parts.append("## Albero delle directory\n\n```text\n")
parts.append(f"{root.name}/\n")
parts.append("\n".join(tree_lines))
parts.append("\n```\n\n")
parts.append("## Indice file sorgente\n\n")
for index, path in enumerate(files, 1):
    parts.append(f"{index}. `{path.relative_to(root).as_posix()}`\n")
parts.append("\n---\n\n## Contenuti\n")

lang_map = {".py": "python", ".html": "html", ".js": "javascript", ".css": "css"}
for path in files:
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = path.read_text(encoding="utf-8", errors="replace")
    lang = lang_map.get(path.suffix.lower(), "")
    parts.append(f"\n### `{rel}`\n\n```{lang}\n")
    parts.append(text)
    if not text.endswith("\n"):
        parts.append("\n")
    parts.append("```\n")

content = "".join(parts)
out.write_text(content, encoding="utf-8")
print(f"written {out}")
print(f"files {len(files)}")
print(f"chars {len(content)}")
print(f"approx_mb {len(content.encode('utf-8')) / (1024 * 1024):.2f}")
