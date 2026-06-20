from pathlib import Path

_REPO_ROOT_MARKERS = ["AGENTS.md", "memory/memory_summary.md"]

def get_repo_root() -> str:
    """Find the repository root by searching upward for known marker files."""
    current = Path.cwd()
    root = current
    while True:
        if any((root / marker).exists() for marker in _REPO_ROOT_MARKERS):
            return str(root)
        parent = root.parent
        if parent == root:  # reached filesystem root
            break
        root = parent
    # fallback to current working directory
    return str(current)
