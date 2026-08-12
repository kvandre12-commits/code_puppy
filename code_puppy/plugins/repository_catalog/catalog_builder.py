"""Build lightweight repo-discovery artifacts for the current workspace."""

from __future__ import annotations

import ast
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

DEFAULT_IGNORES = frozenset(
    {
        ".git",
        ".venv*",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "build",
        "dist",
        "htmlcov",
    }
)
DEFAULT_REPO_MAP_PATH = Path("REPO_MAP.txt")
DEFAULT_CODE_INDEX_PATH = Path("CODE_INDEX.txt")
DEFAULT_CATALOG_PATH = Path("outputs/repository_catalog.json")


@dataclass(slots=True)
class FileCatalogEntry:
    path: str
    classes: list[str]
    functions: list[str]
    imports: list[str]
    docstring_summary: str
    error: str = ""


def _normalize_ignores(ignore_names: Iterable[str] | None) -> set[str]:
    names = {name.strip() for name in (ignore_names or DEFAULT_IGNORES) if name.strip()}
    return names or set(DEFAULT_IGNORES)


def _matches_ignore_name(name: str, ignore_name: str) -> bool:
    if ignore_name.endswith("*"):
        return name.startswith(ignore_name[:-1])
    return name == ignore_name


def _should_ignore(path: Path, ignore_names: set[str]) -> bool:
    return any(
        _matches_ignore_name(part, ignore_name)
        for part in path.parts
        for ignore_name in ignore_names
    )


def _sorted_entries(directory: Path, ignore_names: set[str]) -> list[Path]:
    children = [
        path for path in directory.iterdir() if not _should_ignore(path, ignore_names)
    ]
    return sorted(children, key=lambda path: (not path.is_dir(), path.name.casefold()))


def _render_tree(
    directory: Path, ignore_names: set[str], prefix: str = ""
) -> list[str]:
    lines: list[str] = []
    children = _sorted_entries(directory, ignore_names)
    for index, child in enumerate(children):
        connector = "└── " if index == len(children) - 1 else "├── "
        suffix = "/" if child.is_dir() else ""
        lines.append(f"{prefix}{connector}{child.name}{suffix}")
        if child.is_dir():
            extension = "    " if index == len(children) - 1 else "│   "
            lines.extend(_render_tree(child, ignore_names, prefix + extension))
    return lines


def build_repo_map_text(root: Path, ignore_names: Iterable[str] | None = None) -> str:
    ignore_set = _normalize_ignores(ignore_names)
    return "\n".join([".", *_render_tree(root, ignore_set)]) + "\n"


def discover_python_files(
    root: Path, ignore_names: Iterable[str] | None = None
) -> list[Path]:
    ignore_set = _normalize_ignores(ignore_names)
    files = [
        path
        for path in root.rglob("*.py")
        if path.is_file() and not _should_ignore(path.relative_to(root), ignore_set)
    ]
    return sorted(files)


def _summarize_docstring(docstring: str | None) -> str:
    if not docstring:
        return ""
    for line in docstring.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned
    return ""


def _collect_import_statement(node: ast.stmt) -> list[str]:
    if isinstance(node, ast.Import):
        return [f"import {alias.name}" for alias in node.names]
    if isinstance(node, ast.ImportFrom):
        module = f"{'.' * node.level}{node.module or ''}"
        return [f"from {module} import {alias.name}" for alias in node.names]
    return []


def catalog_python_file(root: Path, file_path: Path) -> FileCatalogEntry:
    relative_path = file_path.relative_to(root).as_posix()
    try:
        source = file_path.read_text(encoding="utf-8")
        module = ast.parse(source, filename=str(file_path))
    except Exception as exc:  # noqa: BLE001 - catalog should never explode.
        return FileCatalogEntry(
            path=relative_path,
            classes=[],
            functions=[],
            imports=[],
            docstring_summary="",
            error=f"{type(exc).__name__}: {exc}",
        )

    classes = [node.name for node in module.body if isinstance(node, ast.ClassDef)]
    functions = [
        node.name
        for node in module.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    imports: list[str] = []
    for node in module.body:
        imports.extend(_collect_import_statement(node))

    return FileCatalogEntry(
        path=relative_path,
        classes=classes,
        functions=functions,
        imports=sorted(set(imports)),
        docstring_summary=_summarize_docstring(ast.get_docstring(module)),
    )


def build_code_index_text(entries: Iterable[FileCatalogEntry]) -> str:
    lines: list[str] = []
    for entry in entries:
        for class_name in entry.classes:
            lines.append(f"{entry.path} class {class_name}")
        for function_name in entry.functions:
            lines.append(f"{entry.path} def {function_name}")
    return "\n".join(lines) + ("\n" if lines else "")


def _json_ready(entries: list[FileCatalogEntry]) -> list[dict[str, Any]]:
    return [asdict(entry) for entry in entries]


def build_repository_artifacts(
    root: str | Path = ".",
    *,
    repo_map_path: str | Path = DEFAULT_REPO_MAP_PATH,
    code_index_path: str | Path = DEFAULT_CODE_INDEX_PATH,
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    ignore_names: Iterable[str] | None = None,
    include_repo_map: bool = True,
    include_code_index: bool = True,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    ignore_set = _normalize_ignores(ignore_names)
    python_files = discover_python_files(root_path, ignore_set)
    entries = [catalog_python_file(root_path, file_path) for file_path in python_files]

    repo_map_output = root_path / Path(repo_map_path)
    code_index_output = root_path / Path(code_index_path)
    catalog_output = root_path / Path(catalog_path)
    catalog_output.parent.mkdir(parents=True, exist_ok=True)

    if include_repo_map:
        repo_map_output.write_text(
            build_repo_map_text(root_path, ignore_set),
            encoding="utf-8",
        )
    if include_code_index:
        code_index_output.write_text(
            build_code_index_text(entries),
            encoding="utf-8",
        )

    payload = {
        "root": str(root_path),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "ignore_names": sorted(ignore_set),
        "python_file_count": len(entries),
        "class_count": sum(len(entry.classes) for entry in entries),
        "function_count": sum(len(entry.functions) for entry in entries),
        "error_count": sum(1 for entry in entries if entry.error),
        "files": _json_ready(entries),
    }
    catalog_output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "root": str(root_path),
        "repo_map_path": str(repo_map_output.relative_to(root_path)),
        "code_index_path": str(code_index_output.relative_to(root_path)),
        "catalog_path": str(catalog_output.relative_to(root_path)),
        "python_file_count": payload["python_file_count"],
        "class_count": payload["class_count"],
        "function_count": payload["function_count"],
        "error_count": payload["error_count"],
        "include_repo_map": include_repo_map,
        "include_code_index": include_code_index,
    }


def query_repository_catalog(
    query: str,
    *,
    root: str | Path = ".",
    catalog_path: str | Path = DEFAULT_CATALOG_PATH,
    limit: int = 20,
) -> dict[str, Any]:
    cleaned_query = query.strip()
    if not cleaned_query:
        return {"ok": False, "error": "Empty query."}

    root_path = Path(root).resolve()
    catalog_file = root_path / Path(catalog_path)
    if not catalog_file.exists():
        return {
            "ok": False,
            "error": f"Catalog not found: {catalog_file.relative_to(root_path)}",
        }

    data = json.loads(catalog_file.read_text(encoding="utf-8"))
    tokens = [token.casefold() for token in cleaned_query.split() if token.strip()]
    matches: list[dict[str, Any]] = []
    for entry in data.get("files", []):
        fields = [
            entry.get("path", ""),
            entry.get("docstring_summary", ""),
            *entry.get("classes", []),
            *entry.get("functions", []),
            *entry.get("imports", []),
        ]
        haystack = " ".join(fields).casefold()
        if all(token in haystack for token in tokens):
            matches.append(entry)

    def _score(entry: dict[str, Any]) -> tuple[int, str]:
        path = entry.get("path", "")
        score = 0
        lowered_path = path.casefold()
        if cleaned_query.casefold() in lowered_path:
            score += 4
        score += sum(
            3
            for name in entry.get("classes", [])
            if cleaned_query.casefold() in name.casefold()
        )
        score += sum(
            3
            for name in entry.get("functions", [])
            if cleaned_query.casefold() in name.casefold()
        )
        score += sum(
            1
            for name in entry.get("imports", [])
            if cleaned_query.casefold() in name.casefold()
        )
        return (-score, path)

    ranked = sorted(matches, key=_score)[: max(1, min(limit, 100))]
    return {
        "ok": True,
        "query": cleaned_query,
        "catalog_path": str(catalog_file.relative_to(root_path)),
        "total_matches": len(matches),
        "matches": ranked,
    }
