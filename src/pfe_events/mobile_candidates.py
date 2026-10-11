"""M10: spatially coherent, persistent apparent-motion residual candidates.

Similarity residuals cannot distinguish every depth/parallax effect from motion.
PERSISTENT_CANDIDATE is deliberately not a confirmed independent moving object.
"""
from dataclasses import dataclass, asdict
import cv2
import numpy as np
from .global_motion import GlobalMotionConfig, fit_apparent_motion


@dataclass(frozen=True)
class CandidateConfig:
    min_support: int = 4
    min_direction_coherence: float = .8
    max_box_area_fraction: float = .15
    consecutive_observations: int = 3
    association_iou: float = .15


def iou(a,b):
    intersection=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    return intersection/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


def warped_box(box,matrix,downsample):
    x1,y1,x2,y2=box
    points=np.array([[x1,y1],[x2,y1],[x2,y2],[x1,y2]],dtype=float)/downsample
    transformed=(points@matrix[:,:2].T+matrix[:,2])*downsample
    return [*transformed.min(axis=0),*transformed.max(axis=0)]


class ResidualCandidateTracker:
    def __init__(self, motion_config=GlobalMotionConfig(), config=CandidateConfig()):
        if (type(config.min_support) is not int or config.min_support<3
            or type(config.consecutive_observations) is not int or config.consecutive_observations<1
            or not 0<config.min_direction_coherence<=1 or not 0<config.max_box_area_fraction<=1
            or not 0<config.association_iou<=1):
            raise ValueError('Invalid candidate configuration')
        self.motion_config=motion_config;self.config=config
        self.previous_end=None;self.previous=[];self.next_id=1

    def parameters(self): return {'motion':asdict(self.motion_config),'candidate':asdict(self.config)}

    def update(self,previous,current,end_us):
        c=self.motion_config; cfg=self.config
        if type(end_us) is not int or (self.previous_end is not None and end_us-self.previous_end!=c.step_us):
            raise ValueError('Contiguous integer timestamps required')
        p,q=np.asarray(previous,dtype=np.float32),np.asarray(current,dtype=np.float32)
        if (p.ndim!=2 or p.shape[1:]!=(2,) or p.shape!=q.shape or not np.isfinite(p).all()
            or not np.isfinite(q).all() or np.any(p<0) or np.any(q<0)
            or np.any(p[:,0]>=c.width/c.downsample) or np.any(q[:,0]>=c.width/c.downsample)
            or np.any(p[:,1]>=c.height/c.downsample) or np.any(q[:,1]>=c.height/c.downsample)):
            raise ValueError('Finite, in-bounds matching working-coordinate Nx2 points required')
        raw=fit_apparent_motion(p,q,c)
        out={'valid':raw['valid'],'status':raw['status'],'raw_motion':raw,
             'regions':[],'tentative_regions':[],'rejections':[],
             'claim':'APPARENT_MOTION_CANDIDATES_NOT_CONFIRMED_INDEPENDENT_OBJECTS'}
        if not raw['valid']:
            self.previous=[];self.previous_end=end_us
            return out
        matrix=np.asarray(raw['matrix_working_pixels'])
        vectors=(q-(p@matrix[:,:2].T+matrix[:,2]))*c.downsample
        norms=np.linalg.norm(vectors,axis=1);unusual=norms>c.residual_native_px
        points=q[unusual]*c.downsample;vectors=vectors[unusual];norms=norms[unusual]
        candidates=[]
        for region in raw['regions']:
            box=region['xyxy']
            inside=(points[:,0]>=box[0])&(points[:,0]<box[2])&(points[:,1]>=box[1])&(points[:,1]<box[3])
            count=int(inside.sum())
            coherence=float(np.linalg.norm(np.mean(vectors[inside]/norms[inside,None],axis=0))) if count else 0.
            area=(box[2]-box[0])*(box[3]-box[1])/(c.width*c.height)
            reasons=[]
            if count<cfg.min_support: reasons.append('LOW_SUPPORT')
            if coherence<cfg.min_direction_coherence: reasons.append('INCOHERENT_DIRECTIONS')
            if area>cfg.max_box_area_fraction: reasons.append('BROAD_REGION')
            if reasons:
                out['rejections'].append({'xyxy':box,'reasons':reasons,'support_points':count,'direction_coherence':coherence})
            else:
                candidates.append({'xyxy':box,'support_points':count,'direction_coherence':coherence,
                    'residual_vector_native_px_per_step':np.median(vectors[inside],axis=0).tolist()})
        # One-to-one association, descending overlap, in the current camera image.
        matches=[]
        for i,old in enumerate(self.previous):
            prediction=warped_box(old['xyxy'],matrix,c.downsample)
            for j,new in enumerate(candidates):
                overlap=iou(prediction,new['xyxy'])
                if overlap>=cfg.association_iou: matches.append((overlap,i,j))
        used_old=set();used_new=set()
        for _,i,j in sorted(matches,reverse=True):
            if i in used_old or j in used_new: continue
            old=self.previous[i];candidates[j].update(candidate_id=old['candidate_id'],
                consecutive_observations=old['consecutive_observations']+1,first_seen_us=old['first_seen_us'])
            used_old.add(i);used_new.add(j)
        for candidate in candidates:
            if 'candidate_id' not in candidate:
                candidate.update(candidate_id=self.next_id,consecutive_observations=1,first_seen_us=end_us)
                self.next_id+=1
            persistent=candidate['consecutive_observations']>=cfg.consecutive_observations
            candidate.update(status='PERSISTENT_CANDIDATE' if persistent else 'TENTATIVE_CANDIDATE',last_seen_us=end_us)
            out['regions' if persistent else 'tentative_regions'].append(candidate)
        self.previous=candidates;self.previous_end=end_us
        out['status']='VALID_CANDIDATE_MODEL'
        return out


class ImageCandidateDetector:
    """M03 LK correspondence settings preserved; candidate logic is separate."""
    def __init__(self, motion_config=GlobalMotionConfig(), config=CandidateConfig()):
        self.motion_config=motion_config;self.tracker=ResidualCandidateTracker(motion_config,config)
        self.previous=None;self.previous_end=None

    def update(self,gray,end_us):
        c=self.motion_config
        if gray.dtype!=np.uint8 or gray.shape!=(c.height//c.downsample,c.width//c.downsample):
            raise ValueError('Expected configured grayscale image')
        if type(end_us) is not int or (self.previous_end is not None and end_us-self.previous_end!=c.step_us):
            raise ValueError('Contiguous image timestamps required')
        empty=np.empty((0,2),np.float32);p,q=empty,empty
        if self.previous is not None:
            points=cv2.goodFeaturesToTrack(self.previous,maxCorners=c.max_features,qualityLevel=.01,minDistance=6,blockSize=5)
            if points is not None:
                lk=dict(winSize=(21,21),maxLevel=2,criteria=(cv2.TERM_CRITERIA_EPS|cv2.TERM_CRITERIA_COUNT,20,.01))
                forward,status,_=cv2.calcOpticalFlowPyrLK(self.previous,gray,points,None,**lk)
                if forward is not None:
                    backward,reverse_status,_=cv2.calcOpticalFlowPyrLK(gray,self.previous,forward,None,**lk)
                    if backward is not None:
                        p0,q0,back=points.reshape(-1,2),forward.reshape(-1,2),backward.reshape(-1,2)
                        keep=((status.ravel()==1)&(reverse_status.ravel()==1)&np.isfinite(q0).all(axis=1)
                            &np.isfinite(back).all(axis=1)&(np.linalg.norm(p0-back,axis=1)<=c.fb_max_px)
                            &(q0[:,0]>=0)&(q0[:,0]<gray.shape[1])&(q0[:,1]>=0)&(q0[:,1]<gray.shape[0]))
                        p,q=p0[keep],q0[keep]
        result=self.tracker.update(p,q,end_us)
        if self.previous is None: result['status']='WARMUP'
        self.previous=gray.copy();self.previous_end=end_us
        return result
