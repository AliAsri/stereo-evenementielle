"""Shared artifact I/O, with explicit compatibility profiles for old reports.

Writers never create parents implicitly. Scientific JSON should use write_json;
the legacy writer is retained only for existing experiment output contracts.
"""
import hashlib
import json
from pathlib import Path


def sha256_file(path):
    """Hash a file in bounded memory, including large event/weight files."""
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    """Strict JSON with ASCII escapes and a trailing newline (M11–M13)."""
    Path(path).write_text(
        json.dumps(value, indent=2, allow_nan=False) + '\n', encoding='utf-8'
    )


def write_legacy_json(path, value):
    """Preserve the original M05/M07–M10 JSON byte format, including NaN."""
    Path(path).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def write_unicode_json(path, value):
    """Strict UTF-8 JSON without a trailing newline (S01/Y01 export)."""
    Path(path).write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False),
        encoding='utf-8',
    )
