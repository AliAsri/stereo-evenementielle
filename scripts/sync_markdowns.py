"""Copy project Markdown files into markdowns/, preserving relative paths."""

import hashlib
import os
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DESTINATION = ROOT / "markdowns"
EXCLUDED = {
    "markdowns", ".git", ".venv", ".venv-demo", "venv", "env", "node_modules",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", ".cache",
}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").digest()


def main():
    if DESTINATION.is_symlink() or DESTINATION.is_junction():
        raise ValueError("markdowns must be a regular directory in the project")
    DESTINATION.mkdir(exist_ok=True)
    copied = 0
    for folder, directories, filenames in os.walk(ROOT, followlinks=False):
        directories[:] = sorted(
            name for name in directories
            if name.lower() not in EXCLUDED
            and not (Path(folder) / name).is_symlink()
            and not (Path(folder) / name).is_junction()
        )
        for filename in sorted(filenames):
            source = Path(folder) / filename
            if source.suffix.lower() != ".md" or source.is_symlink():
                continue
            relative = source.relative_to(ROOT)
            target = DESTINATION / relative
            if not target.resolve().is_relative_to(DESTINATION.resolve()):
                raise ValueError(f"Destination outside markdowns: {relative}")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
            if digest(source) != digest(target):
                raise IOError(f"Copy verification failed: {relative}")
            copied += 1
    print(f"{copied} Markdown files copied and verified in {DESTINATION}")


if __name__ == "__main__":
    main()
