import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WikifyPaths:
    app_root: Path
    base: Path
    scripts: Path
    graph: Path


def discover_app_root() -> Path:
    return Path(__file__).resolve().parent.parent


def discover_workspace_base(start: Path | str | None = None) -> Path | None:
    current = Path(start or os.getcwd()).expanduser().resolve()
    candidates = [current, *current.parents]
    for candidate in candidates:
        if (candidate / 'wikify.json').is_file():
            return candidate
    return None


def discover_base() -> Path:
    env_base = os.environ.get('WIKIFY_BASE') or os.environ.get('FOKB_BASE')
    if env_base:
        return Path(env_base).expanduser().resolve()
    workspace_base = discover_workspace_base()
    if workspace_base:
        return workspace_base
    return discover_app_root()


def build_paths() -> WikifyPaths:
    app_root = discover_app_root()
    base = discover_base()
    return WikifyPaths(
        app_root=app_root,
        base=base,
        scripts=app_root / 'scripts',
        graph=base / 'graph',
    )
