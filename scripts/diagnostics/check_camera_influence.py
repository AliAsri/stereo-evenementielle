"""Post-hoc reference-assisted control; not a proposed production detector."""
import argparse
import json
from pathlib import Path
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from pfe_events.geometry import audit_calibration
from pfe_events.rigid_motion import estimate_rigid_motion
from pfe_events.artifacts import write_json, sha256_file

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=ROOT/'outputs/focused_truck/run_01')
    parser.add_argument('--output', type=Path, required=True, help='Fresh output JSON path')
    args = parser.parse_args()
    out = args.source
    if args.output.exists(): raise FileExistsError('Use a fresh output JSON path')
    report = json.loads((out / 'summary.json').read_text())
    inf = json.loads((out / '400000_inference.json').read_text())
    cal = audit_calibration(ROOT / 'data/raw/zurich_city_04_b/calibration/cam_to_cam.yaml')
    k = np.array([[cal['fx_px'],0,cal['cx_px']],[0,cal['fy_px'],cal['cy_px']],[0,0,1.]])
    with np.load(out / '400000.npz', allow_pickle=False) as a:
        p, q, z = a['previous'], a['current'], a['depth_samples']
        x1,y1,x2,y2 = report['reference_box_valid_only_at_anchor']['xyxy']
        inside = (q[:,0]>=x1)&(q[:,0]<x2)&(q[:,1]>=y1)&(q[:,1]<y2)
        fitting_z = z.copy(); fitting_z[inside] = np.nan
        model = estimate_rigid_motion(p,q,fitting_z,k,previous_us=inf['previous_us'],
            current_us=inf['current_us'],depth_us=inf['depth_us'],depth_source='predicted')
        result = {'status':'NO_USABLE_CONTROL_POSE', 'reference_assisted_diagnostic_only': True,
                  'model':model,'removed_depth_points':int((inside & np.isfinite(z)).sum()),
                  'input_sha256':sha256_file(out/'400000.npz'), 'script_sha256':sha256_file(Path(__file__))}
        if model['valid']:
            selected = inside & np.isfinite(z) & (z>0)
            xyz = np.column_stack(((p[selected,0]-k[0,2])/k[0,0]*z[selected],
                                   (p[selected,1]-k[1,2])/k[1,1]*z[selected],z[selected]))
            t = np.asarray(model['transform_previous_to_current'])
            transformed = xyz @ t[:3,:3].T + t[:3,3]
            front = transformed[:,2]>0
            prediction = (transformed[front] @ k.T)[:,:2]/transformed[front,2,None]
            residual = np.linalg.norm(q[selected][front]-prediction,axis=1)
            result.update(status='COMPLETE', evaluated=int(front.sum()),
                          baseline_median_px=report['frames'][-1]['residual_px']['median'],
                          control_median_px=float(np.median(residual)), control_max_px=float(residual.max()),
                          control_candidates_over_3px=int((residual>3).sum()),residuals_px=residual.tolist())
    write_json(args.output,result)
    print(json.dumps({key:val for key,val in result.items() if key not in ('model','residuals_px')}))


if __name__ == '__main__':
    main()
