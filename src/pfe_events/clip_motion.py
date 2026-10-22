"""Recompute the frozen 20 ms seed check and 100 ms rigid diagnostic from events."""
import time
import cv2
import numpy as np
from .representations import rectified_counts, normalized_event_image
from .rectified_tracking import checked_tracks, sample_disparity_depth
from .rigid_ambiguity import guarded_rigid_motion
from .stereo import predict_stereo, StereoConfig


class ClipMotionCache:
    """Six exact-date stereo results from one immutable replay context.

    Only current results computed by the caller are retained. A missing date
    falls back to raw-event computation, never to the closest available depth.
    Arrays are owned, read-only copies; no predictions are loaded from disk.
    """
    def __init__(self, readers, maps, calibration, normalizer):
        self.context = (*readers, *maps, calibration, normalizer)
        self.frames = {}
        self.latest_us = None

    def check_context(self, readers, maps, calibration, normalizer, end_us):
        context = (*readers, *maps, calibration, normalizer)
        if (len(context) != len(self.context)
                or any(a is not b for a, b in zip(context, self.context))
                or (self.latest_us is not None and self.latest_us > end_us)):
            raise ValueError('Cache requires the same replay context and no future frames')

    def remember(self, end_us, images, disparity, valid):
        if (type(end_us) is not int
                or (self.latest_us is not None and end_us <= self.latest_us)
                or len(images) != 2 or disparity.ndim != 2
                or valid.shape != disparity.shape or valid.dtype != bool
                or any(im.shape != disparity.shape or im.dtype != np.uint8 for im in images)):
            raise ValueError('Increasing integer dates and matching stereo arrays required')
        stored = tuple(np.array(a, copy=True, order='C') for a in (*images, disparity, valid))
        for array in stored:
            array.flags.writeable = False
        self.frames[end_us] = stored
        self.latest_us = end_us
        for date in list(self.frames):
            if date < end_us - 100000:
                del self.frames[date]
        while len(self.frames) > 6:
            del self.frames[min(self.frames)]

    def get(self, end_us):
        return self.frames.get(end_us)


def track_seeds(previous, current, points, *, max_level=2):
    """Historical LK/FB rule, including an explicit empty-track abstention."""
    points = np.asarray(points, dtype=np.float32)
    if type(max_level) is not int or max_level not in (2, 3):
        raise ValueError('LK level must be default 2 or explicit experimental 3')
    if (previous.ndim != 2 or previous.shape != current.shape
            or previous.dtype != np.uint8 or current.dtype != np.uint8
            or points.ndim != 2 or points.shape[1:] != (2,)
            or not np.isfinite(points).all()):
        raise ValueError('Matching grayscale uint8 images and finite Nx2 seeds required')
    if not len(points):
        return points.copy(), np.zeros(0, bool), np.empty(0)
    lk = dict(winSize=(21,21), maxLevel=max_level,
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


def infer_clip_motion(readers, maps, calibration, normalizer, current, *, end_us,
                      history_cache=None, stereo_executor=None):
    """History computed in this replay; only slices at or before end_us are used.

    Frozen selection: seeds at t-100 ms checked against t-80 ms, then tracked
    directly to t. Previous stereo depth belongs to t-100 ms, never to t.
    Exact-date current stereo results may be reused from the bounded cache.
    """
    if type(end_us) is not int or len(readers)!=2 or len(maps)!=2:
        raise ValueError('Integer end time and left/right readers/maps required')
    if any(end_us-150000 < r.first_us or end_us > r.last_us for r in readers):
        raise ValueError('Complete 150 ms causal history required')
    if history_cache is not None:
        history_cache.check_context(readers, maps, calibration, normalizer, end_us)
    start=end_us-100000
    begin=time.perf_counter()
    def image(reader, mapping, end):
        events=reader.window(end-50000,end)
        counts,_=rectified_counts(events,mapping)
        return np.ascontiguousarray(normalized_event_image(counts,normalizer,total_only=True))
    cached_previous = history_cache.get(start) if history_cache is not None else None
    cached_short = history_cache.get(start+20000) if history_cache is not None else None
    previous=(cached_previous[:2] if cached_previous is not None else
              [image(r,m,start) for r,m in zip(readers,maps)])
    short=(cached_short[0] if cached_short is not None else
           image(readers[0],maps[0],start+20000))
    represented=time.perf_counter()
    if cached_previous is None:
        disparity,valid,_,_=predict_stereo(*previous,StereoConfig(), executor=stereo_executor)
    else:
        disparity,valid=cached_previous[2:]
    stereo_done=time.perf_counter()
    p,_,tracking=checked_tracks(previous[0],short)
    seeds_done=time.perf_counter()
    z,_=sample_disparity_depth(p,disparity,valid,calibration['q'])
    depth_done=time.perf_counter()
    q,keep,fb=track_seeds(previous[0],current,p)
    ids=np.flatnonzero(keep); p,q,z,fb=p[keep],q[keep],z[keep],fb[keep]
    tracked=time.perf_counter()
    k=np.array([[calibration['fx_px'],0,calibration['cx_px']],
                [0,calibration['fy_px'],calibration['cy_px']],[0,0,1.]])
    guarded=guarded_rigid_motion(p,q,z,k,previous_us=start,current_us=end_us,
                                 depth_us=start,depth_source='predicted')
    model=guarded['final']
    finished=time.perf_counter()
    arrays=dict(previous=p,current=q,depth_samples=z,fb_px=fb,seed_ids=ids)
    details=dict(seed_tracking=tracking,
                 rigid_ambiguity={key:value for key,value in guarded.items() if key != 'final'},
                 history_reuse=dict(previous_stereo=cached_previous is not None,
                                    short_image=cached_short is not None),
                 history_windows_us=[[start-50000,start],
                     [start-50000,start],[start-30000,start+20000]],
                 timing_ms=dict(history_read_representation=(represented-begin)*1000,
                                previous_stereo=(stereo_done-represented)*1000,
                                depth_sampling=(depth_done-seeds_done)*1000,
                                tracking=((seeds_done-stereo_done)+(tracked-depth_done))*1000,
                                rigid_fit=(finished-tracked)*1000,total=(finished-begin)*1000))
    return arrays,model,details
