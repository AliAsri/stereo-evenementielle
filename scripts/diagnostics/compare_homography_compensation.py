"""One frozen comparison of depth-free homography against archived 3D predictions."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def estimate(previous, current, parameters):
    """Observations only: no depth, camera pose or reference segmentation."""
    p, q = np.asarray(previous, dtype=float), np.asarray(current, dtype=float)
    size = parameters['frame_size']
    if (p.ndim != 2 or p.shape[1:] != (2,) or q.shape != p.shape
            or not np.isfinite(p).all() or not np.isfinite(q).all()
            or np.any(p < 0) or np.any(q < 0) or np.any(p >= size) or np.any(q >= size)):
        raise ValueError('Finite matching in-bounds Nx2 observations required')
    out = dict(valid=False, status='INSUFFICIENT_SUPPORT', homography=None,
               tracks=len(p), evaluated_points=0, inliers=0, inlier_fraction=0.,
               hull_fraction=0., residual_px=[None]*len(p), point_status=['UNKNOWN']*len(p))
    if len(p) < parameters['min_points']:
        return out
    # Fixed baseline only; do not choose among repeated fits.
    cv2.setRNGSeed(parameters['rng_seed'])
    h, _ = cv2.findHomography(p, q, cv2.RANSAC, parameters['ransac_px'],
                             maxIters=parameters['iterations'], confidence=parameters['confidence'])
    if h is None or not np.isfinite(h).all() or np.linalg.matrix_rank(h) < 3:
        out['status'] = 'FIT_REJECTED'
        return out
    homogeneous = np.column_stack((p, np.ones(len(p)))) @ h.T
    good = np.isfinite(homogeneous).all(axis=1) & (np.abs(homogeneous[:, 2]) > 1e-12)
    predicted = np.full_like(p, np.nan)
    predicted[good] = homogeneous[good, :2]/homogeneous[good, 2, None]
    residual = np.linalg.norm(predicted-q, axis=1)
    good &= np.isfinite(residual)
    inliers = good & (residual <= parameters['ransac_px'])
    count = int(inliers.sum())
    hull = (float(cv2.contourArea(cv2.convexHull(p[inliers].astype(np.float32))))
            / (size[0]*size[1])) if count >= 3 else 0.
    out.update(inliers=count, inlier_fraction=count/len(p), hull_fraction=hull)
    if (count < parameters['min_inliers'] or count/len(p) < parameters['min_fraction']
            or hull < parameters['min_hull_fraction']):
        out['status'] = 'CONSENSUS_REJECTED'
        return out
    statuses = np.full(len(p), 'UNKNOWN', dtype=object)
    statuses[good] = 'MODEL_CONSISTENT'
    statuses[good & (residual > parameters['residual_px'])] = 'RESIDUAL_CANDIDATE'
    out.update(valid=True, status='VALID_DOMINANT_IMAGE_MODEL', homography=h.tolist(),
               evaluated_points=int(good.sum()), point_status=statuses.tolist(),
               residual_px=[float(r) if ok else None for r, ok in zip(residual, good)])
    return out


def counts(model, moving):
    status = np.asarray(model['point_status'])
    candidate = status == 'RESIDUAL_CANDIDATE'
    return dict(evaluated=model['evaluated_points'], unknown=int((status == 'UNKNOWN').sum()),
                static_candidates=int((candidate & ~moving).sum()),
                moving_candidates=int((candidate & moving).sum()))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding='utf-8'))
    source = ROOT/protocol['source']
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    for name, digest in protocol['source_hashes'].items():
        if sha(source/name) != digest:
            raise ValueError('Changed archived input: '+name)
    output = args.protocol.parent/'result'
    output.mkdir(exist_ok=False)
    shutil.copy2(__file__, output/Path(__file__).name)
    shutil.copy2(args.protocol, output/'protocol.json')
    baseline = {row['name']: row['diagnostic']['primary'] for row in
                json.loads((source/'summary.json').read_text(encoding='utf-8'))['rows']}
    cv2.setNumThreads(2)
    cv2.ocl.setUseOpenCL(False)
    rows, previous_observations, predictions = [], [], []
    for name in protocol['cases']:
        with np.load(source/(name+'.npz'), allow_pickle=False) as scene:
            p, q = scene['previous'], scene['current']
            duplicate = next((i for i, (a, b) in enumerate(previous_observations)
                              if np.array_equal(p, a) and np.array_equal(q, b)), None)
            model = (estimate(p, q, protocol['parameters']) if duplicate is None
                     else copy.deepcopy(predictions[duplicate]))
            previous_observations.append((p.copy(), q.copy()))
            predictions.append(model)
            old, new = counts(baseline[name], scene['moving']), counts(model, scene['moving'])
            rows.append(dict(name=name, primary_3d=old, homography_2d=new, model=model,
                             reused_prediction_from=None if duplicate is None else rows[duplicate]['name'],
                             no_regression=(new['static_candidates'] <= old['static_candidates']
                                 and new['moving_candidates'] >= old['moving_candidates']
                                 and new['evaluated'] >= old['evaluated'])))
    by_name = {r['name']: r for r in rows}
    criteria = {n: by_name[n]['no_regression'] for n in protocol['acceptance']['cases']}
    missing = by_name['missing_depth']['homography_2d']
    criteria['missing_depth_usable_without_static_candidates'] = (
        missing['evaluated'] > 0 and missing['static_candidates'] == 0)
    result = dict(criteria=criteria, rows=rows, unique_fits=len(set(
        r['name'] if r['reused_prediction_from'] is None else r['reused_prediction_from'] for r in rows)),
        decision='SYNTHETIC_ONLY_REQUIRES_VALIDATION' if all(criteria.values()) else 'RETAIN_3D_COMPENSATION',
        protocol_sha256=sha(args.protocol), script_sha256=sha(Path(__file__)),
        opencv=cv2.__version__, numpy=np.__version__, promoted=False,
        scope='Exact synthetic correspondences only. No real-world motion validation or speed claim.')
    (output/'summary.json').write_text(json.dumps(result, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(criteria))
    print(result['decision'])
    for row in rows:
        print(row['name'], row['model']['status'], row['primary_3d'], row['homography_2d'])


if __name__ == '__main__':
    main()
