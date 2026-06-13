"""Resolve RoboLab USD scene assets without taking a hard Isaac dependency.

The release path for this bridge is to import RoboLab as a package. During
local development we also support a sibling RoboLab checkout, which keeps the
DEXTRAH render scripts usable before packaging is finalized.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


ACCEPTED_SCENE_EXTENSIONS = (".usda", ".usdc", ".usdz", ".usd")


@dataclass(frozen=True)
class ResolvedRoboLabScene:
    """Resolved RoboLab scene asset and the source that provided it."""

    scene_path: Path
    scene_dir: Path | None
    source: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_candidate_scene_dirs(
    *,
    robolab_root: str | Path | None = None,
    scene_dir: str | Path | None = None,
) -> Iterator[tuple[Path, str]]:
    if scene_dir:
        yield Path(scene_dir).expanduser(), "argument:scene_dir"

    env_scene_dir = os.environ.get("ROBOLAB_SCENE_DIR")
    if env_scene_dir:
        yield Path(env_scene_dir).expanduser(), "env:ROBOLAB_SCENE_DIR"

    roots: list[tuple[Path, str]] = []
    if robolab_root:
        roots.append((Path(robolab_root).expanduser(), "argument:robolab_root"))

    env_root = os.environ.get("ROBOLAB_ROOT")
    if env_root:
        roots.append((Path(env_root).expanduser(), "env:ROBOLAB_ROOT"))

    try:
        import robolab.constants as robolab_constants  # type: ignore

        constants_scene_dir = getattr(robolab_constants, "SCENE_DIR", None)
        if constants_scene_dir:
            yield Path(constants_scene_dir).expanduser(), "package:robolab.constants.SCENE_DIR"
    except Exception:
        pass

    workspace_robolab = _repo_root().parent / "RoboLab"
    roots.append((workspace_robolab, "workspace:RoboLab"))

    seen_roots: set[Path] = set()
    for root, source in roots:
        root = root.expanduser()
        if root in seen_roots:
            continue
        seen_roots.add(root)
        yield root / "assets" / "scenes", source


def _iter_scene_files(scene_dir: Path, ignore_directories: Iterable[str] = ("not_used", "tmp")) -> Iterator[Path]:
    ignore = set(ignore_directories)
    if not scene_dir.is_dir():
        return
    for root, dirs, files in os.walk(scene_dir):
        dirs[:] = [d for d in dirs if d not in ignore and not d.startswith("_")]
        for filename in files:
            path = Path(root) / filename
            if path.suffix.lower() in ACCEPTED_SCENE_EXTENSIONS:
                yield path


def _find_scene_file(scene: str | Path, scene_dir: Path) -> Path | None:
    requested = Path(scene)
    requested_posix = requested.as_posix()
    for candidate in _iter_scene_files(scene_dir):
        rel = candidate.relative_to(scene_dir).as_posix()
        if candidate.name == requested_posix or rel == requested_posix or rel.endswith(f"/{requested_posix}"):
            return candidate.resolve()
    return None


def resolve_robolab_scene(
    scene: str | Path,
    *,
    robolab_root: str | Path | None = None,
    scene_dir: str | Path | None = None,
) -> ResolvedRoboLabScene:
    """Resolve a RoboLab scene by absolute path, relative path, or filename.

    Args:
        scene: Scene filename, path relative to a RoboLab scenes directory, or
            absolute USD path.
        robolab_root: Optional RoboLab repository/package root. Its
            ``assets/scenes`` directory is searched.
        scene_dir: Optional scene directory searched before all other sources.

    Raises:
        FileNotFoundError: If the scene cannot be found in any candidate source.
    """

    scene_path = Path(scene).expanduser()
    if scene_path.is_absolute():
        if not scene_path.exists():
            raise FileNotFoundError(f"RoboLab scene path does not exist: {scene_path}")
        if scene_path.suffix.lower() not in ACCEPTED_SCENE_EXTENSIONS:
            raise ValueError(f"RoboLab scene must be a USD file, got: {scene_path}")
        return ResolvedRoboLabScene(scene_path=scene_path.resolve(), scene_dir=scene_path.parent.resolve(), source="absolute")

    searched: list[str] = []
    for candidate_dir, source in _iter_candidate_scene_dirs(robolab_root=robolab_root, scene_dir=scene_dir):
        candidate_dir = candidate_dir.expanduser()
        searched.append(f"{source}:{candidate_dir}")
        found = _find_scene_file(scene_path, candidate_dir)
        if found is not None:
            return ResolvedRoboLabScene(scene_path=found, scene_dir=candidate_dir.resolve(), source=source)

    searched_text = "\n  - ".join(searched) if searched else "<none>"
    raise FileNotFoundError(f"Could not resolve RoboLab scene '{scene}'. Searched:\n  - {searched_text}")


def iter_robolab_scenes(
    *,
    robolab_root: str | Path | None = None,
    scene_dir: str | Path | None = None,
) -> Iterator[ResolvedRoboLabScene]:
    """Yield all RoboLab scenes visible through the configured search paths."""

    seen: set[Path] = set()
    for candidate_dir, source in _iter_candidate_scene_dirs(robolab_root=robolab_root, scene_dir=scene_dir):
        if not candidate_dir.is_dir():
            continue
        for scene_path in _iter_scene_files(candidate_dir):
            resolved = scene_path.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            yield ResolvedRoboLabScene(scene_path=resolved, scene_dir=candidate_dir.resolve(), source=source)
