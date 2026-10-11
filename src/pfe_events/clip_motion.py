"""Recompute the frozen 20 ms seed check and 100 ms rigid diagnostic from events."""
import time
import cv2
import numpy as np
from .geometry import reproject_q
from .representations import rectified_counts, normalized_event_image
from .rectified_tracking import checked_tracks, sample_masked_depth
from .rigid_motion import estimate_rigid_motion
from .stereo import predict_stereo, StereoConfig


def track_seeds(previous, current, points):
    """Historical LK/FB rule, including an explicit empty-track abstention."""
    points = np.asarray(points, dtype=np.float32)
    if (previous.ndim != 2 or previous.shape != current.shape
            or previous.dtype != np.uint8 or current.dtype != np.uint8
            or points.ndim != 2 or points.shape[1:] != (2,)
            or not np.isfinite(points).all()):
        raise ValueError('Matching grayscale uint8 images and finite Nx2 seeds required')
    if not len(points):
        return points.copy(), np.zeros(0, bool), np.empty(0)
    lk = dict(winSize=(21,21), maxLevel=2,
              criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT,20,.01))
    features = np.ascontiguousarray(points.reshape(-1,1,2))
    forward, good, _ = cv2.calcOpticalFlowPyrLK(previous,current,features,None,**lk)
    if forward is None:
        return np.full_like(points,np.nan),np.zeros(len(points),bool),np.full(len(points),np.nan)
    backward, reverse_good, _ = cv2.calcOpticalFlowPyrLK(current,previous,forward,None,**lk)
    if backward is None:
        return forward.reshape(-1,2),np.zeros(len(points),bool),np.full(len(points),np.nan)
    q, back = forward.reshape(-1,2),backward.reshape(-1,2)
    fb = np.linalg.norm(back-points,axis=1)
    h,w=previous.shape
    keep=((good.ravel()==1)&(reverse_good.ravel()==1)&np.isfinite(q).all(axis=1)
          &np.isfinite(back).all(axis=1)&(fb<=1)&(q>=0).all(axis=1)
          &(q[:,0]<w)&(q[:,1]<h))
    return q,keep,fb


def infer_clip_motion(readers, maps, calibration, normalizer, current, *, end_us):
    """All history computed now; only event slices at or before end_us are used.

    Frozen selection: seeds at t-100 ms checked against t-80 ms, then tracked
    directly to t. Previous stereo depth belongs to t-100 ms, never to t.
    """
    if type(end_us) is not int or len(readers)!=2 or len(maps)!=2:
        raise ValueError('Integer end time and left/right readers/maps required')
    if any(end_us-150000 < r.first_us or end_us > r.last_us for r in readers):
        raise ValueError('Complete 150 ms causal history required')
    start=end_us-100000
    begin=time.perf_counter()
    def image(reader, mapping, end):
        events=reader.window(end-50000,end)
        counts,_=rectified_counts(events,mapping)
        return np.ascontiguousarray(normalized_event_image(counts,normalizer)[...,2])
    previous=[image(r,m,start) for r,m in zip(readers,maps)]
    short=image(readers[0],maps[0],start+20000)
    represented=time.perf_counter()
    disparity,valid,_,_=predict_stereo(*previous,StereoConfig())
    yy,xx=np.indices(disparity.shape)
    depth=reproject_q(xx,yy,disparity,calibration['q'])[...,2].astype(np.float32)
    stereo_done=time.perf_counter()
    p,_,tracking=checked_tracks(previous[0],short)
    z,_=sample_masked_depth(p,depth,valid)
    q,keep,fb=track_seeds(previous[0],current,p)
    ids=np.flatnonzero(keep); p,q,z,fb=p[keep],q[keep],z[keep],fb[keep]
    tracked=time.perf_counter()
    k=np.array([[calibration['fx_px'],0,calibration['cx_px']],
                [0,calibration['fy_px'],calibration['cy_px']],[0,0,1.]])
    model=estimate_rigid_motion(p,q,z,k,previous_us=start,current_us=end_us,
                               depth_us=start,depth_source='predicted')
    finished=time.perf_counter()
    arrays=dict(previous=p,current=q,depth_samples=z,fb_px=fb,seed_ids=ids)
    details=dict(seed_tracking=tracking,history_windows_us=[[start-50000,start],
                     [start-50000,start],[start-30000,start+20000]],
                 timing_ms=dict(history_read_representation=(represented-begin)*1000,
                                previous_stereo_depth=(stereo_done-represented)*1000,
                                tracking=(tracked-stereo_done)*1000,
                                rigid_fit=(finished-tracked)*1000,total=(finished-begin)*1000))
    return arrays,model,details
