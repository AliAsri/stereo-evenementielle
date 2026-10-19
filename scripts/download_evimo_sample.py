"""Acquire frozen EVIMO examples with hard transfer and extraction caps.

Default/--next-train-sequence select the historical train samples;
--validation-reference selects the approved eval IMO/SfM pair. No inference.

The gzip archive is streamed only as far as that sequence. No pickle is loaded.
The downloaded prefix is not a verified complete gzip/archive; individual files
have local SHA256 provenance (not a publisher-provided integrity signature).
"""
import hashlib
import argparse
import json
import re
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

# Approved 19 October: new eval recordings, acquisition/qualification only.
# Each gzip prefix gets a fixed half of the common cap, before reading data.
VALIDATION_TARGETS = (
    ('imo', 'scene14_dyn_test_03_000000'),
    ('sfm', 'scene_03_00_000000'),
)
VALIDATION_NETWORK_LIMIT = 512 * 1024**2
VALIDATION_EXTRACT_LIMIT = 4 * 1024**3


class TransferLimit(ValueError):
    pass


class SharedBudgetReader:
    """Count every returned HTTP body byte, including discarded gzip prefixes."""
    def __init__(self, source, budget, local_limit):
        self.source, self.budget, self.local_limit = source, budget, local_limit
        self.count = 0
        self.digest = hashlib.sha256()

    def read(self, size=-1):
        if size == 0:
            return b''
        remaining = min(self.local_limit - self.count,
                        self.budget['limit'] - self.budget['read'])
        if remaining <= 0:
            raise TransferLimit('HTTP body transfer cap reached; no automatic retry')
        size = min(size if size >= 0 else remaining, remaining)
        data = self.source.read(size)
        self.count += len(data)
        self.budget['read'] += len(data)
        self.digest.update(data)
        return data


def acquire_validation_sequence(root, out, category, name, budget, extraction,
                                local_limit, *, opener=None):
    """Stream one fixed allowlist; never extract unrelated archive members."""
    if (category, name) not in VALIDATION_TARGETS:
        raise ValueError('Sequence is not in the approved validation plan')
    sequence = f'left_camera/{category}/eval/{name}'
    destination = root/'data/raw/evimo2v2'/sequence
    if destination.exists():
        raise FileExistsError('Existing sequence must not be reacquired or overwritten')
    url = f'https://obj.umiacs.umd.edu/evimo2v2npz/npz_left_camera_{category}.tar.gz'
    report = dict(status='STARTED', url=url, sequence=sequence, official_split='eval',
                  http_limit_bytes=local_limit, files=[], visited_members=[],
                  archive_integrity='Partial gzip prefix; no full archive CRC/trailer verification',
                  started_utc=datetime.now(timezone.utc).isoformat())
    reader = None
    opener = urllib.request.urlopen if opener is None else opener
    try:
        request = urllib.request.Request(url, headers={
            'Range': f'bytes=0-{local_limit-1}', 'Accept-Encoding': 'identity'})
        with opener(request, timeout=45) as response:
            report['http_status'] = response.status
            report['http_headers'] = dict(response.headers)
            match = re.fullmatch(r'bytes 0-(\d+)/(\d+)',
                                 response.headers.get('Content-Range', ''))
            if (response.status != 206 or not match or int(match[1]) >= local_limit
                    or int(match[2]) <= int(match[1])
                    or response.headers.get('Content-Encoding', 'identity') != 'identity'):
                raise ValueError('Expected an identity HTTP range within the fixed prefix cap')
            reader = SharedBudgetReader(response, budget, local_limit)
            with tarfile.open(fileobj=reader, mode='r|gz') as archive:
                for member in archive:
                    report['visited_members'].append(dict(name=member.name, bytes=member.size))
                    selected = selected_name(member, sequence)
                    if selected is None:
                        continue
                    if any(f['name'] == selected for f in report['files']):
                        raise ValueError('Duplicate selected archive member')
                    if member.size > extraction['limit'] - extraction['written']:
                        raise ValueError('Common extraction cap would be exceeded')
                    destination.mkdir(parents=True, exist_ok=True)
                    partial = destination/(selected+'.part')
                    target = destination/selected
                    if target.exists():
                        raise FileExistsError('Never overwrite an existing acquired file')
                    digest, copied = hashlib.sha256(), 0
                    with archive.extractfile(member) as source, partial.open('xb') as target_stream:
                        while chunk := source.read(1024**2):
                            target_stream.write(chunk)
                            extraction['written'] += len(chunk)
                            digest.update(chunk)
                            copied += len(chunk)
                    if copied != member.size:
                        raise IOError('Incomplete selected archive member')
                    partial.rename(target)
                    # Verify the saved file, not just the bytes passed to write().
                    with target.open('rb') as saved:
                        saved_hash = hashlib.file_digest(saved, 'sha256').hexdigest()
                    if target.stat().st_size != copied or saved_hash != digest.hexdigest():
                        raise IOError('Saved file size/hash mismatch')
                    report['files'].append(dict(name=selected,
                        path=target.relative_to(root).as_posix(), bytes=copied, sha256=saved_hash))
                    print(f'{sequence}/{selected}: {copied} saved bytes', flush=True)
                    if {f['name'] for f in report['files']} == FILES:
                        report['status'] = 'ACQUIRED_UNAUDITED'
                        break
                else:
                    raise ValueError('Fixed sequence is absent or incomplete in this archive')
    except TransferLimit as error:
        report.update(status='TRANSFER_CAP_REACHED', error=str(error))
    except Exception as error:
        report.update(status='INCOMPLETE', error=f'{type(error).__name__}: {error}')
    finally:
        if reader is not None:
            report['transferred_bytes'] = reader.count
            report['transferred_prefix_sha256'] = reader.digest.hexdigest()
        else:
            report['transferred_bytes'] = 0
        if report['status'] == 'STARTED':
            report['status'] = 'INTERRUPTED'
        report['ended_utc'] = datetime.now(timezone.utc).isoformat()
        (out/f'{category}_acquisition.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


def acquire_validation_references(root, out):
    if out.exists():
        raise FileExistsError('Use a fresh acquisition directory; no automatic resume/retry')
    for category, name in VALIDATION_TARGETS:
        if (root/'data/raw/evimo2v2'/f'left_camera/{category}/eval/{name}').exists():
            raise FileExistsError('Approved target already exists; inspect without downloading')
    out.mkdir(parents=True)
    plan = dict(status='APPROVED_ACQUISITION_ONLY', targets=[dict(category=c, sequence=n)
                for c,n in VALIDATION_TARGETS], files=sorted(FILES),
                authorization='User approved acquisition and qualification of the two proposed targets; no inference/training',
                created_utc=datetime.now(timezone.utc).isoformat(),
                network_limit_bytes=VALIDATION_NETWORK_LIMIT,
                per_archive_limit_bytes=VALIDATION_NETWORK_LIMIT//2,
                extraction_limit_bytes=VALIDATION_EXTRACT_LIMIT,
                allocation='Two fixed 256 MiB prefixes, no borrowing or retry',
                inference=False, training=False,
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
    (out/'acquisition_plan.json').write_text(json.dumps(plan, indent=2), encoding='utf-8')
    budget = dict(limit=VALIDATION_NETWORK_LIMIT, read=0)
    extraction = dict(limit=VALIDATION_EXTRACT_LIMIT, written=0)
    reports = []
    for category, name in VALIDATION_TARGETS:
        print(f'Acquiring fixed eval target {category}/{name}; prefix cap 256 MiB', flush=True)
        reports.append(acquire_validation_sequence(root, out, category, name,
            budget, extraction, VALIDATION_NETWORK_LIMIT//2))
        print(f'{category}: {reports[-1]["status"]}; common body bytes {budget["read"]}', flush=True)
    report = dict(status='ACQUIRED_UNAUDITED' if all(r['status']=='ACQUIRED_UNAUDITED' for r in reports)
                  else 'INCOMPLETE', network_limit_bytes=budget['limit'],
                  transferred_bytes=budget['read'], extracted_bytes=extraction['written'],
                  targets=[dict(sequence=r['sequence'], status=r['status'], files=len(r['files']))
                           for r in reports], inference=False, training=False,
                  next_action='Qualify complete targets only; no outcome-based replacement or cap increase')
    (out/'acquisition.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    return report


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


def selected_name(member, sequence=SEQUENCE):
    """Return an allowlisted basename only; never materialize archive paths."""
    path = PurePosixPath(member.name)
    if path.parent.as_posix() != sequence or path.name not in FILES:
        return None
    if not member.isfile() or member.size < 0:
        raise ValueError('Selected member must be a regular file')
    return path.name


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--next-train-sequence', action='store_true',
                        help='First different train sequence in archive order; fixed 512 MiB transfer cap')
    parser.add_argument('--validation-reference', action='store_true',
                        help='Approved fixed eval IMO/SfM pair; common 512 MiB cap, no inference')
    parser.add_argument('--output', type=Path, help='Fresh acquisition report directory')
    args = parser.parse_args()
    if args.validation_reference:
        if args.next_train_sequence or args.output is None:
            parser.error('--validation-reference requires fresh --output and excludes --next-train-sequence')
        result = acquire_validation_references(ROOT, args.output)
        return 0 if result['status'] == 'ACQUIRED_UNAUDITED' else 2
    if args.next_train_sequence and args.output is None:
        parser.error('--next-train-sequence requires a fresh --output')
    sequence = None if args.next_train_sequence else SEQUENCE
    network_limit = 512*1024**2 if args.next_train_sequence else NETWORK_LIMIT
    out = args.output if args.output is not None else ROOT / 'outputs/motion/M14'
    destination = ROOT / 'data/raw/evimo2v2' / sequence if sequence else None
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / 'acquisition.json'
    if manifest_path.exists() or (destination is not None and destination.exists()):
        raise FileExistsError('Existing acquisition must be inspected, not overwritten')
    if destination is not None:
        destination.mkdir(parents=True)
    report = {
        'status': 'STARTED', 'started_utc': datetime.now(timezone.utc).isoformat(),
        'url': URL, 'sequence': sequence, 'official_split': 'train',
        'selection': ('First train sequence in archive order different from original sample; no outcome-based choice'
                      if args.next_train_sequence else 'First archive sequence; train directory verified before extraction; no model results consulted'),
        'data_license': 'CC BY-SA 4.0',
        'source_page': 'https://better-flow.github.io/evimo/download_evimo_2.html',
        'network_limit_bytes': network_limit, 'extraction_limit_bytes': EXTRACT_LIMIT,
        'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': [], 'visited_members': [],
        'archive_integrity': 'Partial gzip stream; no full gzip trailer check or publisher checksum',
    }
    manifest_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    reader = None
    try:
        request = urllib.request.Request(URL, headers={'Range': f'bytes=0-{network_limit-1}'})
        with urllib.request.urlopen(request, timeout=45) as response:
            report['http_status'] = response.status
            report['http_headers'] = dict(response.headers)
            if response.status != 206 or not response.headers.get('Content-Range', '').startswith('bytes 0-'):
                raise ValueError('Expected verified partial HTTP response starting at byte zero')
            reader = BoundedReader(response, network_limit)
            extracted = 0
            with tarfile.open(fileobj=reader, mode='r|gz') as archive:
                for member in archive:
                    report['visited_members'].append({'name': member.name, 'bytes': member.size})
                    if sequence is None:
                        path = PurePosixPath(member.name)
                        if (not member.isfile() or len(path.parts) != 5
                                or path.parts[:3] != ('left_camera', 'imo', 'train')
                                or path.parent.as_posix() == SEQUENCE or path.name not in FILES):
                            continue
                        if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-' for c in path.parts[3]):
                            raise ValueError('Unexpected sequence directory name')
                        sequence = path.parent.as_posix()
                        destination = ROOT/'data/raw/evimo2v2'/sequence
                        if destination.exists():
                            raise FileExistsError('Next sequence already exists; inspect it without overwriting')
                        destination.mkdir(parents=True)
                        report['sequence'] = sequence
                        print('Selected ' + sequence, flush=True)
                    name = selected_name(member, sequence)
                    if name is None:
                        # Stop before traversing any other sequence's data.
                        if member.isfile() and not member.name.startswith(sequence + '/'):
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
    raise SystemExit(main())
