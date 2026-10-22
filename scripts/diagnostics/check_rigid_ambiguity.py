"""Frozen synthetic ambiguity diagnostic. Never imported by the DSEC pipeline."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from pfe_events.rigid_motion import estimate_rigid_motion, RigidMotionConfig
from pfe_events.rigid_controls import make_scene, project


def project_transform(xyz, intrinsic, transform):
    t = np.asarray(transform)
    moved = xyz @ t[:3, :3].T + t[:3, 3]
    good = np.isfinite(moved).all(axis=1) & (moved[:, 2] > 1e-6)
    pixels = np.full((len(xyz), 2), np.nan)
    pixels[good] = project(moved[good], intrinsic)
    good &= np.isfinite(pixels).all(axis=1)
    return pixels, good


def diagnose(previous, current, depth_m, intrinsic, *, previous_us, current_us,
             depth_us, depth_source):
    """At most two fits; accepts observations only, never reference labels/pose."""
    config = RigidMotionConfig()
    p, q, z, k = (np.asarray(a) for a in (previous, current, depth_m, intrinsic))
    times = dict(previous_us=previous_us, current_us=current_us,
                 depth_us=depth_us, depth_source=depth_source)
    primary = estimate_rigid_motion(p, q, z, k, **times)
    out = dict(primary=primary, secondary=None, secondary_indices=[],
               secondary_denominator=0, common_projectable_points=0,
               median_model_separation_px=None, fits=1,
               ambiguity='AMBIGUITY_NOT_DETECTED', reason='PRIMARY_REJECTED',
               final=copy.deepcopy(primary))
    if not primary['valid']:
        return out
    residual = np.array([np.nan if e is None else e for e in primary['residual_px']])
    ids = np.flatnonzero(np.isfinite(z) & (z > 0) & np.isfinite(residual)
                        & (residual > config.residual_px))
    out.update(secondary_indices=ids.tolist(), secondary_denominator=len(ids),
               reason='SECONDARY_TOO_SMALL')
    if len(ids) < config.min_points:
        return out
    secondary = estimate_rigid_motion(p[ids], q[ids], z[ids], k, **times)
    out.update(secondary=secondary, fits=2, reason='SECONDARY_REJECTED')
    if not secondary['valid']:
        return out
    usable = np.isfinite(z) & (z > 0)
    xyz = np.column_stack(((p[usable, 0]-k[0, 2])/k[0, 0]*z[usable],
                           (p[usable, 1]-k[1, 2])/k[1, 1]*z[usable], z[usable]))
    a, good_a = project_transform(xyz, k, primary['transform_previous_to_current'])
    b, good_b = project_transform(xyz, k, secondary['transform_previous_to_current'])
    common = good_a & good_b
    out.update(common_projectable_points=int(common.sum()), reason='TOO_FEW_COMMON_POINTS')
    if common.sum() < config.min_points:
        return out
    separation = float(np.median(np.linalg.norm(a[common]-b[common], axis=1)))
    out.update(median_model_separation_px=separation, reason='MODELS_NOT_DISTINCT')
    if separation > config.residual_px:
        out.update(ambiguity='AMBIGUOUS_RIGID_MODELS', reason='COMPETING_SUPPORTED_MODELS')
        out['final'].update(valid=False, status='AMBIGUOUS_RIGID_MODELS',
                            transform_previous_to_current=None, evaluated_points=0,
                            residual_px=[None]*len(p), predicted_pixels=[None]*len(p),
                            point_status=['UNKNOWN']*len(p))
    return out


def concurrent_worlds():
    """Two physical references with exactly identical detector observations."""
    row, col = np.indices((9, 12))
    x, y = np.meshgrid(np.linspace(65, 575, 12), np.linspace(55, 425, 9))
    p = np.column_stack((x.ravel(), y.ravel()))
    z = (6+6*((row+col)%3)).ravel().astype(float)
    group_b = (col % 3 == 0).ravel()
    k = np.array([[500., 0, 320], [0, 500, 240], [0, 0, 1]])
    xyz = np.column_stack(((p[:, 0]-320)/500*z, (p[:, 1]-240)/500*z, z))
    moved = xyz.copy()
    moved[:, 0] += np.where(group_b, -.08, .08)
    q = project(moved, k)
    worlds = []
    for name, camera_x, moving, object_x in (
            ('world_A', .08, group_b, -.16), ('world_B', -.08, ~group_b, .16)):
        physical = xyz.copy()
        physical[moving, 0] += object_x
        physical[:, 0] += camera_x
        np.testing.assert_allclose(project(physical, k), q, rtol=0, atol=1e-12)
        transform = np.eye(4); transform[0, 3] = camera_x
        worlds.append(dict(kind=name, previous=p.copy(), current=q.copy(), depth_m=z.copy(),
                           intrinsic=k.copy(), transform=transform, moving=moving.copy(),
                           previous_us=0, current_us=100000))
    return worlds


def pose_error(model, truth):
    if not model['valid']:
        return None
    transform = np.asarray(model['transform_previous_to_current'])
    cosine = (np.trace(transform[:3, :3] @ truth[:3, :3].T)-1)/2
    return dict(rotation_deg=float(np.degrees(np.arccos(np.clip(cosine, -1, 1)))),
                translation_m=float(np.linalg.norm(transform[:3, 3]-truth[:3, 3])))


def evaluate(name, scene, result):
    """References enter only here, after the diagnostic prediction."""
    primary, final = result['primary'], result['final']
    moving = scene['moving']
    def counts(model):
        statuses = np.array(model['point_status'])
        return dict(evaluated=model['evaluated_points'], unknown=int((statuses=='UNKNOWN').sum()),
                    residual_candidates=int((statuses=='RESIDUAL_CANDIDATE').sum()),
                    candidates_on_static=int(((statuses=='RESIDUAL_CANDIDATE') & ~moving).sum()),
                    moving_model_consistent=int(((statuses=='MODEL_CONSISTENT') & moving).sum()))
    return dict(name=name, diagnostic=result, primary_exactly_preserved=primary==final,
                primary_counts=counts(primary), final_counts=counts(final),
                added_unknown_points=counts(final)['unknown']-counts(primary)['unknown'],
                primary_pose_error=pose_error(primary, scene['transform']),
                secondary_pose_error=(pose_error(result['secondary'], scene['transform'])
                                      if result['secondary'] is not None else None),
                final_pose_error=pose_error(final, scene['transform']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Fresh diagnostic result directory')
    args = parser.parse_args()
    protocol_path = ROOT/'outputs/motion/rigid_ambiguity_20261019/protocol.json'
    protocol = json.loads(protocol_path.read_text(encoding='utf-8'))
    def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
    if hashlib.sha256(protocol['protocol_section'].encode()).hexdigest() != protocol['protocol_section_sha256']:
        raise ValueError('Changed protocol text')
    for name, digest in protocol['source_sha256'].items():
        if sha(ROOT/name) != digest: raise ValueError(f'Changed frozen source: {name}')
    args.output.mkdir(parents=True, exist_ok=False)
    snapshot = args.output/'source'; snapshot.mkdir()
    for name in [*protocol['source_sha256'], 'scripts/diagnostics/check_rigid_ambiguity.py']:
        shutil.copy2(ROOT/name, snapshot/Path(name).name)
    shutil.copy2(protocol_path, args.output/'protocol.json')
    cv2.setNumThreads(2); cv2.ocl.setUseOpenCL(False)
    names = ('static', 'camera_translation', 'camera_rotation', 'object_translation',
             'combined', 'object_rotation', 'missing_depth', 'biased_near_depth', 'dominant_moving_layer')
    scenes = [(name, make_scene(name, seed=0, noise_px=0)) for name in names]
    scenes.append(('combined_noise_02', make_scene('combined', seed=7, noise_px=.2)))
    scenes.extend((s['kind'], s) for s in concurrent_worlds())
    # Save all fixed observations and references before any model prediction.
    inputs = {}
    for name, scene in scenes:
        path = args.output/(name+'.npz')
        np.savez(path, **{k:v for k,v in scene.items() if isinstance(v, np.ndarray)})
        inputs[name] = dict(sha256=sha(path), previous_us=scene['previous_us'], current_us=scene['current_us'])
    (args.output/'inputs.json').write_text(json.dumps(inputs, indent=2), encoding='utf-8')
    rows = []; concurrent_prediction = None
    for name, scene in scenes:
        if name == 'world_B':
            # Identical detector inputs: one prediction evaluated against both worlds.
            result = copy.deepcopy(concurrent_prediction)
        else:
            result = diagnose(scene['previous'], scene['current'], scene['depth_m'], scene['intrinsic'],
                              previous_us=scene['previous_us'], current_us=scene['current_us'],
                              depth_us=scene['previous_us'], depth_source='synthetic_reference')
            if name == 'world_A': concurrent_prediction = result
        rows.append(evaluate(name, scene, result))
    by_name = {r['name']:r for r in rows}
    criteria = dict(simple_cases_preserved=all(by_name[n]['primary_exactly_preserved'] for n in
                    (*names[:6], 'combined_noise_02')),
                    missing_depth_preserved=by_name['missing_depth']['primary_exactly_preserved']
                        and not by_name['missing_depth']['diagnostic']['final']['valid'],
                    concurrent_worlds_abstain=all(by_name[n]['diagnostic']['ambiguity']=='AMBIGUOUS_RIGID_MODELS'
                        and by_name[n]['diagnostic']['final']['transform_previous_to_current'] is None
                        for n in ('world_A','world_B')),
                    identical_observations_same_prediction=by_name['world_A']['diagnostic']==by_name['world_B']['diagnostic'])
    report = dict(status='COMPLETED', date='2026-10-20', criteria=criteria,
                  conclusion='SYNTHETIC_CRITERIA_PASSED' if all(criteria.values()) else 'HYPOTHESIS_NOT_RETAINED',
                  rows=rows, protocol_sha256=sha(protocol_path), diagnostic_sha256=sha(Path(__file__)),
                  frozen_source_sha256=protocol['source_sha256'],
                  versions=dict(python=sys.version, numpy=np.__version__, opencv=cv2.__version__),
                  opencv_threads=cv2.getNumThreads(), opencl=cv2.ocl.useOpenCL(),
                  scope='Synthetic geometry only; no event sensor, LK or SGBM simulation, no real-world motion validation',
                  promoted_to_dsec=False)
    (args.output/'summary.json').write_text(json.dumps(report, indent=2, allow_nan=False), encoding='utf-8')
    print(json.dumps(criteria));print(report['conclusion'])
    for r in rows:
        d=r['diagnostic'];print(r['name'],d['primary']['status'],d['secondary_denominator'],d['ambiguity'],r['added_unknown_points'])


if __name__ == '__main__':
    main()
