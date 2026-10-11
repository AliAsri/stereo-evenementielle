"""Acquire one predetermined official train sequence, with hard byte budgets.

The gzip archive is streamed only as far as that sequence. No pickle is loaded.
The downloaded prefix is not a verified complete gzip/archive; individual files
have local SHA256 provenance (not a publisher-provided integrity signature).
"""
import hashlib
import json
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://obj.umiacs.umd.edu/evimo2v2npz/npz_left_camera_imo.tar.gz'
SEQUENCE = 'left_camera/imo/train/scene13_dyn_test_02_000000'
NETWORK_LIMIT = 256 * 1024**2
EXTRACT_LIMIT = 2 * 1024**3
FILES = {
    'dataset_events_p.npy', 'dataset_events_t.npy', 'dataset_events_xy.npy',
    'dataset_info.npz', 'dataset_mask.npz', 'dataset_depth.npz',
}


class BoundedReader:
    def __init__(self, source, limit):
        self.source, self.limit, self.count = source, limit, 0
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        if self.count >= self.limit:
            raise ValueError('Compressed transfer budget reached')
        size = min(size if size >= 0 else self.limit, self.limit - self.count)
        data = self.source.read(size)
        self.count += len(data)
        self.digest.update(data)
        return data


def selected_name(member):
    """Return an allowlisted basename only; never materialize archive paths."""
    path = PurePosixPath(member.name)
    if path.parent.as_posix() != SEQUENCE or path.name not in FILES:
        return None
    if not member.isfile() or member.size < 0:
        raise ValueError('Selected member must be a regular file')
    return path.name


def main():
    out = ROOT / 'outputs/motion/M14'
    destination = ROOT / 'data/raw/evimo2v2' / SEQUENCE
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'acquisition.json'
    if manifest_path.exists() or destination.exists():
        raise FileExistsError('Existing acquisition must be inspected, not overwritten')
    destination.mkdir(parents=True)
    report = {
        'status': 'STARTED', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'url': URL, 'sequence': SEQUENCE, 'official_split': 'train',
        'selection': 'First archive sequence; train directory verified before extraction; no model results consulted',
        'data_license': 'CC BY-SA 4.0',
        'source_page': 'https://better-flow.github.io/evimo/download_evimo_2.html',
        'network_limit_bytes': NETWORK_LIMIT, 'extraction_limit_bytes': EXTRACT_LIMIT,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': [], 'visited_members': [],
        'archive_integrity': 'Partial gzip stream; no full gzip trailer check or publisher checksum',
    }
    reader = None
    try:
        request = urllib.request.Request(URL, headers={'Range': f'bytes=0-{NETWORK_LIMIT-1}'})
        with urllib.request.urlopen(request, timeout=45) as response:
            report['http_status'] = response.status
            report['http_headers'] = dict(response.headers)
            if response.status != 206 or not response.headers.get('Content-Range', '').startswith('bytes 0-'):
                raise ValueError('Expected verified partial HTTP response starting at byte zero')
            reader = BoundedReader(response, NETWORK_LIMIT)
            extracted = 0
            with tarfile.open(fileobj=reader, mode='r|gz') as archive:
                for member in archive:
                    report['visited_members'].append({'name': member.name, 'bytes': member.size})
                    name = selected_name(member)
                    if name is None:
                        # Stop before traversing any other sequence's data.
                        if member.isfile() and not member.name.startswith(SEQUENCE + '/'):
                            raise ValueError('Selected sequence incomplete before another sequence')
                        continue
                    if any(f['name'] == name for f in report['files']):
                        raise ValueError('Duplicate archive member')
                    extracted += member.size
                    if extracted > EXTRACT_LIMIT:
                        raise ValueError('Extraction budget exceeded')
                    partial = destination / (name + '.part')
                    digest, copied = hashlib.sha256(), 0
                    with archive.extractfile(member) as source, partial.open('xb') as target:
                        while chunk := source.read(1024**2):
                            target.write(chunk)
                            digest.update(chunk)
                            copied += len(chunk)
                    if copied != member.size:
                        raise IOError('Incomplete member')
                    partial.rename(destination / name)
                    report['files'].append({'name': name, 'path': (destination / name).relative_to(ROOT).as_posix(),
                                            'bytes': copied, 'sha256': digest.hexdigest()})
                    print(f'{name}: {copied} bytes; transfer {reader.count} bytes', flush=True)
                    if {f['name'] for f in report['files']} == FILES:
                        report['status'] = 'ACQUIRED_UNAUDITED'
                        break
                else:
                    raise ValueError('Missing required sequence files')
    except Exception as error:
        report['status'] = 'INCOMPLETE'
        report['error'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        if reader:
            report['transferred_bytes'] = reader.count
            report['transferred_prefix_sha256'] = reader.digest.hexdigest()
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        manifest_path.write_text(json.dumps(report, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
