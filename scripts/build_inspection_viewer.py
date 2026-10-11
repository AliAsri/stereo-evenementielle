"""Package existing integrated results as one offline HTML inspection viewer."""
import argparse
import base64
from io import BytesIO
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))


def validate_track_alignment(arrays, model):
    """Reject incomplete saved tracks before zip can silently truncate them."""
    points = arrays['current']
    if points.ndim != 2 or points.shape[1:] != (2,):
        raise ValueError('Current tracks must have shape Nx2')
    count = len(points)
    if (arrays['previous'].shape != points.shape or arrays['depth_samples'].shape != (count,)
            or any(len(model[key]) != count for key in
                   ('point_status', 'predicted_pixels', 'residual_px'))):
        raise ValueError('Track arrays and model records must have matching lengths')


def load_sensitivity(folder, frames, summary_path, hashes):
    """Attach a saved hypothesis only to the exact predictions it was derived from."""
    import numpy as np
    from pfe_events.artifacts import sha256_file
    from pfe_events.residual_regions import group_residual_regions
    folder=folder.resolve()
    report_path=folder/'summary.json'; arrays_path=folder/'frame8_sensitivity.npz'
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if report['status']!='FIXED_INPUT_POSE_SENSITIVITY_DIAGNOSTIC':
        raise ValueError('Completed pose sensitivity diagnostic required')
    for name,digest in report['input_sha256'].items():
        if sha256_file(ROOT/name)!=digest: raise ValueError(f'Sensitivity source changed: {name}')
    expected=report['input_sha256'].get(str(summary_path.relative_to(ROOT)))
    if expected!=sha256_file(summary_path): raise ValueError('Sensitivity belongs to another source')
    if sha256_file(arrays_path)!=report['artifact_sha256'][arrays_path.name]:
        raise ValueError('Sensitivity arrays changed')
    target=report['observed'][1]['timestamp_us']; previous=report['observed'][0]['timestamp_us']
    index=next(i for i,f in enumerate(frames) if f['timestamp_us']==target)
    if index==0 or frames[index-1]['timestamp_us']!=previous:
        raise ValueError('Sensitivity dates do not match adjacent viewer frames')
    frame=frames[index]; points=np.asarray([t['current'] for t in frame['tracks']])
    original=np.asarray([np.nan if t['residual'] is None else t['residual'] for t in frame['tracks']])
    predicted=np.asarray([[np.nan,np.nan] if t['predicted'] is None else t['predicted'] for t in frame['tracks']])
    with np.load(arrays_path,allow_pickle=False) as a:
        np.testing.assert_allclose(a['residual_T8'],original,atol=1e-10,rtol=0,equal_nan=True)
        np.testing.assert_allclose(a['predicted_T8'],predicted,atol=1e-10,rtol=0,equal_nan=True)
        residual=a['residual_T7']; prediction=a['predicted_T7']; valid=a['valid']
        if residual.shape!=original.shape or prediction.shape!=points.shape or valid.dtype!=bool:
            raise ValueError('Invalid sensitivity shapes or validity mask')
        if not np.array_equal(valid,np.isfinite(original)) or not np.array_equal(valid,np.isfinite(residual)):
            raise ValueError('Sensitivity must retain the same evaluated points')
        np.testing.assert_allclose(residual[valid],np.linalg.norm(points[valid]-prediction[valid],axis=1),atol=1e-10,rtol=0)
        changed=valid&((original>3)!=(residual>3))
        if not np.array_equal(changed,a['changed']): raise ValueError('Changed-point mask mismatch')
        regions=group_residual_regions(points,residual,model_valid=True)
        hypothesis=report['frame8_with_T7_hypothesis']
        if regions!=hypothesis['regions'] or int(changed.sum())!=hypothesis['changed_status']:
            raise ValueError('Sensitivity report differs from arrays')
        tracks=[dict(predicted=prediction[i].tolist() if valid[i] else None,
                     residual=float(residual[i]) if valid[i] else None,
                     status='UNKNOWN' if not valid[i] else 'RESIDUAL_CANDIDATE' if residual[i]>3 else 'MODEL_CONSISTENT',
                     changed=bool(changed[i])) for i in range(len(points))]
    for path in (report_path,arrays_path): hashes[str(path.relative_to(ROOT))]=sha256_file(path)
    return dict(frame_index=index,previous_pose_image=index,target_image=index+1,
        timestamp_us=target,tracks=tracks,regions=regions,evaluated=int(valid.sum()),changed=int(changed.sum()),
        original_candidates=int((valid&(original>3)).sum()),hypothesis_candidates=int((valid&(residual>3)).sum()),
        candidates_to_consistent=int((valid&(original>3)&(residual<=3)).sum()),
        consistent_to_candidates=int((valid&(original<=3)&(residual>3)).sum()))


def load_clip_sensitivity(folder, frames, summary_path, hashes):
    """Read per-date sensitivity, verifying dates and counts against saved arrays."""
    import numpy as np
    from pfe_events.artifacts import sha256_file
    folder=folder.resolve(); report_path=folder/'summary.json'; arrays_path=folder/'transitions.npz'
    report=json.loads(report_path.read_text(encoding='utf-8'))
    if report['status']!='CLIP_POSE_SENSITIVITY_DIAGNOSTIC':
        raise ValueError('Completed clip sensitivity diagnostic required')
    for name,digest in report['input_sha256'].items():
        if sha256_file(ROOT/name)!=digest: raise ValueError(f'Clip sensitivity source changed: {name}')
    if report['input_sha256'].get(str(summary_path.relative_to(ROOT)))!=sha256_file(summary_path):
        raise ValueError('Clip sensitivity belongs to another source')
    if sha256_file(arrays_path)!=report['artifact_sha256'][arrays_path.name]:
        raise ValueError('Clip sensitivity arrays changed')
    if len(report['transitions'])!=len(frames)-1:
        raise ValueError('One sensitivity record per transition required')
    result=[None]
    with np.load(arrays_path,allow_pickle=False) as arrays:
        for index,row in enumerate(report['transitions'],1):
            frame=frames[index]; previous=frames[index-1]
            if (row['from_image']!=index or row['to_image']!=index+1
                    or row['timestamp_us']!=frame['timestamp_us']
                    or row['previous_pose_current_us']!=previous['timestamp_us']):
                raise ValueError('Clip sensitivity dates or image order differ')
            prefix=f'image_{index+1:02d}_'
            original=np.array([np.nan if t['residual'] is None else t['residual'] for t in frame['tracks']])
            points=np.array([t['current'] for t in frame['tracks']])
            residual=arrays[prefix+'residual_previous_pose']; prediction=arrays[prefix+'prediction_previous_pose']
            common=arrays[prefix+'common_valid']; changed=arrays[prefix+'changed']
            if (residual.shape!=original.shape or prediction.shape!=points.shape or common.shape!=original.shape
                    or changed.shape!=original.shape or common.dtype!=bool or changed.dtype!=bool):
                raise ValueError('Invalid clip sensitivity shapes or masks')
            original_valid=np.isfinite(original); alternative_valid=np.isfinite(residual)
            if not np.array_equal(common,original_valid&alternative_valid): raise ValueError('Common support differs')
            np.testing.assert_allclose(residual[alternative_valid],
                np.linalg.norm(points[alternative_valid]-prediction[alternative_valid],axis=1),atol=1e-10,rtol=0)
            expected_changed=common&((original>3)!=(residual>3))
            if not np.array_equal(changed,expected_changed): raise ValueError('Changed points differ')
            counts=dict(tracks=len(original),common_evaluated=int(common.sum()),changed_points=int(changed.sum()),
                original_evaluated=int(original_valid.sum()),hypothesis_evaluated=int(alternative_valid.sum()),
                validity_changed=int((original_valid!=alternative_valid).sum()),
                original_candidates_common=int((common&(original>3)).sum()),
                hypothesis_candidates_common=int((common&(residual>3)).sum()))
            if any(row[key]!=value for key,value in counts.items()): raise ValueError('Clip sensitivity counts differ')
            percent=100*counts['changed_points']/counts['common_evaluated'] if counts['common_evaluated'] else None
            if ((percent is None)!=(row['changed_percent'] is None)
                    or percent is not None and not np.isclose(percent,row['changed_percent'],atol=1e-10,rtol=0)):
                raise ValueError('Clip sensitivity percentage differs')
            result.append(dict(timestamp_us=frame['timestamp_us'],previous_pose_image=index,
                changed=counts['changed_points'],evaluated=counts['common_evaluated'],percent=percent,
                validity_changed=counts['validity_changed']))
    for path in (report_path,arrays_path): hashes[str(path.relative_to(ROOT))]=sha256_file(path)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'outputs/focused_truck/integrated_03')
    parser.add_argument('--output',type=Path,required=True,help='Fresh viewer directory')
    parser.add_argument('--sensitivity',type=Path,help='Optional saved pose-switch diagnostic; no inference rerun')
    parser.add_argument('--clip-sensitivity',type=Path,help='Optional saved sensitivity for every transition')
    args=parser.parse_args()
    args.source=args.source.resolve()
    import numpy as np
    from PIL import Image
    from pfe_events.artifacts import sha256_file,write_json
    from pfe_events.dsec import load_rectify_map
    from pfe_events.object_surface import mapped_roi
    from pfe_events.residual_regions import group_residual_regions
    if args.output.exists(): raise FileExistsError('Use a fresh viewer directory')
    summary_path=args.source/'summary.json'
    summary=json.loads(summary_path.read_text())
    if summary['status']!='COMPLETE_FRESH_OFFLINE_PIPELINE':
        raise ValueError('Completed fresh integrated replay required')
    mapping_path=ROOT/'data/raw'/summary['sequence']/'events_left/rectify_map.h5'
    mapping=load_rectify_map(mapping_path)
    template=Path(__file__).with_name('inspection_viewer.html')
    hashes={str(p.relative_to(ROOT)):sha256_file(p) for p in (summary_path,mapping_path,template,Path(__file__),ROOT/'src/pfe_events/residual_regions.py')}
    def png(array):
        buffer=BytesIO();Image.fromarray(array).save(buffer,format='PNG')
        return 'data:image/png;base64,'+base64.b64encode(buffer.getvalue()).decode('ascii')
    # JSON records name their sibling NPZ; match timestamps, never infer a frame from labels.
    records={}
    for path in args.source.glob('[0-9]*.json'):
        row=json.loads(path.read_text())
        if row['timestamp_us'] in records: raise ValueError('Duplicate frame timestamp')
        records[row['timestamp_us']]=path
    frames=[]
    for expected in summary['frames']:
        path=records[expected['timestamp_us']];row=json.loads(path.read_text())
        if row!=expected: raise ValueError('Frame record differs from summary')
        npz=path.with_suffix('.npz')
        for p in (path,npz): hashes[str(p.relative_to(ROOT))]=sha256_file(p)
        with np.load(npz,allow_pickle=False) as a:
            native,rectified=a['native'],a['rectified']
            points=a['current']; model=row['motion_model']
            validate_track_alignment(a,model)
            tracks=[]
            for i,(p,q,z) in enumerate(zip(a['previous'],points,a['depth_samples'])):
                tracks.append(dict(previous=p.tolist(),current=q.tolist(),
                    predicted=model['predicted_pixels'][i],residual=model['residual_px'][i],
                    status=model['point_status'][i],previous_depth_m=float(z) if np.isfinite(z) else None))
            for obj in row['objects']:
                pixels=mapped_roi(obj['native_xyxy'],mapping,rectified.shape)
                mask=np.zeros(rectified.shape,bool);mask[pixels[:,1],pixels[:,0]]=True
                indices=np.rint(points).astype(int)
                inside=((indices>=0).all(axis=1)&(indices<[rectified.shape[1],rectified.shape[0]]).all(axis=1))
                ids=np.flatnonzero(inside)
                ids=ids[mask[indices[ids,1],indices[ids,0]]]
                obj['point_indices']=ids.tolist()
                if len(ids)!=obj['motion_support']['tracked_points']: raise ValueError('Mapped track support mismatch')
                for status in ('UNKNOWN','MODEL_CONSISTENT','RESIDUAL_CANDIDATE'):
                    if sum(tracks[i]['status']==status for i in ids)!=obj['motion_support'][status]:
                        raise ValueError('Motion counts mismatch')
            residuals=[np.nan if v is None else v for v in model['residual_px']]
            regions=group_residual_regions(points,residuals,model_valid=model['valid'])
            for region in regions:
                members=set(region['point_indices'])
                region['yolo_support']=[dict(detection_index=i,shared_points=len(members.intersection(obj['point_indices'])))
                    for i,obj in enumerate(row['objects']) if members.intersection(obj['point_indices'])]
            frames.append(dict(timestamp_us=row['timestamp_us'],offset_ms=row['offset_ms'],regions=regions,
                compute_ms=row['timing_ms']['full_pipeline'],native=png(native),rectified=png(rectified),
                objects=row['objects'],tracks=tracks,model_valid=model['valid']))
    data=dict(sequence=summary['sequence'],step_ms=summary['step_us']/1000,
              window_ms=summary['window_us']/1000,interval_ms=summary['motion_interval_us']/1000,frames=frames)
    data['sensitivity']=load_sensitivity(args.sensitivity,frames,summary_path,hashes) if args.sensitivity else None
    data['clip_sensitivity']=load_clip_sensitivity(args.clip_sensitivity,frames,summary_path,hashes) if args.clip_sensitivity else None
    serialized=json.dumps(data,ensure_ascii=True,allow_nan=False).replace('<','\\u003c')
    html=template.read_text(encoding='utf-8')
    if html.count('__VIEWER_DATA__')!=1: raise ValueError('Expected one data placeholder')
    args.output.mkdir(parents=True)
    target=args.output/'index.html';target.write_text(html.replace('__VIEWER_DATA__',serialized),encoding='utf-8')
    write_json(args.output/'regions.json',dict(status='GROUPED_SAVED_RESIDUALS',
        policy=dict(threshold_px=3,cell_px=32,dilation=3,connectivity=8,min_points=3,padding_px=8),
        meaning='Spatial proposals only, no object identities, motion labels or measured quality',
        frames=[dict(timestamp_us=f['timestamp_us'],regions=f['regions']) for f in frames]))
    write_json(args.output/'manifest.json',dict(status='BUILT',source=str(args.source.relative_to(ROOT)),
        frames=len(frames),input_sha256=hashes,html_sha256=sha256_file(target),
        meaning='Read-only inspection of saved predictions; no labels, inference or quality evaluation created'))
    print(f'Built {target}: {len(frames)} frames, {target.stat().st_size} bytes; mapped motion counts verified')


if __name__=='__main__':main()
