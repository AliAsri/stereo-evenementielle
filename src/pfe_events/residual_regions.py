"""M03 spatial grouping applied to rectified rigid residuals; no object identity."""
import cv2
import numpy as np


def group_residual_regions(points, residuals, *, model_valid, frame_size=(640,480)):
    """Fixed M03 settings: >3 px, 32 px cells, 3x3 dilation, 8-connectivity,
    >=3 points, 8 px box padding. Return original indices, not new tracks.
    A chain of occupied cells can merge different surfaces into one region.
    """
    p=np.asarray(points,dtype=float);r=np.asarray(residuals,dtype=float)
    if (type(model_valid) is not bool or len(frame_size)!=2
            or any(type(v) is not int or v<=0 for v in frame_size)
            or p.ndim!=2 or p.shape[1:]!=(2,) or r.shape!=(len(p),)
            or not np.isfinite(p).all() or np.any(p<0) or np.any(p>=frame_size)
            or np.isinf(r).any() or np.any(r[np.isfinite(r)]<0)):
        raise ValueError('In-bounds Nx2 points, N nonnegative residuals/NaN and boolean validity required')
    if not model_valid: return []
    ids=np.flatnonzero(np.isfinite(r)&(r>3))
    if not len(ids): return []
    selected=p[ids];width,height=frame_size
    grid=np.zeros(((height+31)//32,(width+31)//32),np.uint8)
    gx,gy=(selected//32).astype(int).T
    grid[gy,gx]=1
    _,labels=cv2.connectedComponents(cv2.dilate(grid,np.ones((3,3),np.uint8)),connectivity=8)
    regions=[]
    for label in np.unique(labels[gy,gx]):
        members=ids[labels[gy,gx]==label]
        if label==0 or len(members)<3: continue
        lo=np.maximum(np.floor(p[members].min(axis=0)-8),[0,0]).astype(int)
        hi=np.minimum(np.ceil(p[members].max(axis=0)+8),[width,height]).astype(int)
        regions.append(dict(xyxy=[*lo.tolist(),*hi.tolist()],point_indices=members.tolist(),
            support_points=len(members),median_residual_px=float(np.median(r[members])),
            max_residual_px=float(r[members].max()),coordinate_frame='camRect0',
            kind='RESIDUAL_REGION_NOT_CONFIRMED_OBJECT'))
    return regions
