"""Pack, restore or verify the frozen inputs of the existing DSEC demo.

Uses only Python's standard library. Does not download or deserialize weights.
The versioned configs/demo_assets.json is the expected content identity.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
MAX_BUNDLE_BYTES = 64 * 1024**2


def destination(root, name):
    relative = PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError(f'Unsafe asset path: {name}')
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f'Asset outside project: {name}')
    return path


def valid_bytes(data, entry):
    return len(data) == entry['bytes'] and hashlib.sha256(data).hexdigest() == entry['sha256']


def file_matches(path, entry):
    if not path.is_file() or path.stat().st_size != entry['bytes']:
        return False
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() == entry['sha256']


def publish(temporary, target):
    # Never replace an existing file, including one created concurrently.
    if os.name == 'nt':
        temporary.rename(target)
    else:
        target.hardlink_to(temporary)


def pack(root, archive, entries):
    if archive.exists():
        raise FileExistsError(f'Use a fresh archive path: {archive}')
    payloads = {}
    for entry in entries:
        path = destination(root, entry['path'])
        if not file_matches(path, entry):
            raise ValueError(f'Missing or changed asset: {entry["path"]}')
        data = path.read_bytes()
        if not valid_bytes(data, entry):
            raise ValueError(f'Asset changed while reading: {entry["path"]}')
        payloads[entry['path']] = data
    archive.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=archive.parent, suffix='.part', delete=False) as stream:
        temporary = Path(stream.name)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            for name, data in payloads.items():
                zipped.writestr(name, data)
        publish(temporary, archive)
    finally:
        temporary.unlink(missing_ok=True)


def restore(root, archive, entries):
    expected = {entry['path']: entry for entry in entries}
    payloads = {}
    with zipfile.ZipFile(archive) as zipped:
        members = zipped.infolist()
        if len(members) != len(expected) or {m.filename for m in members} != set(expected):
            raise ValueError('Archive must contain exactly the expected assets, without duplicates')
        for member in members:
            entry = expected[member.filename]
            if member.file_size != entry['bytes']:
                raise ValueError(f'Unexpected asset size: {member.filename}')
            data = zipped.read(member)  # Also validates ZIP CRC.
            if not valid_bytes(data, entry):
                raise ValueError(f'Asset checksum mismatch: {member.filename}')
            payloads[member.filename] = data
    # Validate every destination before installing anything.
    targets = {name: destination(root, name) for name in expected}
    for name, path in targets.items():
        if path.exists() and not file_matches(path, expected[name]):
            raise FileExistsError(f'Existing asset differs: {path}')
    for name, path in targets.items():
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix='.part', delete=False) as stream:
            temporary = Path(stream.name)
        try:
            temporary.write_bytes(payloads[name])
            publish(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--pack', type=Path, help='Create a new ZIP of the three prepared assets')
    mode.add_argument('--restore', type=Path, help='Restore a trusted bundle into this checkout')
    mode.add_argument('--verify', action='store_true', help='Hash all eight inputs, including raw DSEC files')
    args = parser.parse_args()
    spec = json.loads((ROOT/'configs/demo_assets.json').read_text(encoding='utf-8'))
    if spec['schema'] != 1:
        raise ValueError('Unsupported asset specification')
    entries = spec['files']
    if len({entry['path'] for entry in entries}) != len(entries):
        raise ValueError('Duplicate asset paths')
    for entry in entries:
        destination(ROOT, entry['path'])
    bundled = [entry for entry in entries if entry['bundled']]
    if any(entry['bytes'] < 0 for entry in entries) or sum(e['bytes'] for e in bundled) > MAX_BUNDLE_BYTES:
        raise ValueError('Bundle exceeds size budget')
    if args.pack:
        pack(ROOT, args.pack.resolve(), bundled)
        print(f'Created {args.pack}: {len(bundled)} prepared assets; raw DSEC excluded.')
    elif args.restore:
        restore(ROOT, args.restore, bundled)
        print(f'Restored or verified {len(bundled)} prepared assets; now acquire DSEC and run --verify.')
    else:
        failures = [entry['path'] for entry in entries
                    if not file_matches(destination(ROOT, entry['path']), entry)]
        if failures:
            raise ValueError('Missing or changed demo inputs:\n- ' + '\n- '.join(failures))
        print(f'All {len(entries)} input sizes and SHA256 hashes match the frozen specification.')


if __name__ == '__main__':
    main()
