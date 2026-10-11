"""Ideal point-correspondence controls, not simulated event-camera recordings."""
import numpy as np

KINDS=('fixed_static','global_translation','local_motion','combined_motion',
       'incoherent_noise','parallax_counterexample','local_rotation')


def control_points(kind,moving=True):
    if kind not in KINDS: raise ValueError('Unknown control')
    x,y=np.meshgrid(np.linspace(20,290,10),np.linspace(20,210,8))
    background=np.column_stack([x.ravel(),y.ravel()])
    x,y=np.meshgrid(np.linspace(120,150,4),np.linspace(90,110,3))
    patch=np.column_stack([x.ravel(),y.ravel()])
    p=np.vstack([background,patch]).astype(np.float32)
    camera=np.array([2,0] if kind in ('global_translation','combined_motion','parallax_counterexample') else [0,0],np.float32)
    q=p+camera
    if moving and kind in ('local_motion','combined_motion','parallax_counterexample'):
        q[-12:]+=[4,0]
    elif moving and kind=='incoherent_noise':
        q[-12:]+=np.tile(np.array([[4,0],[-4,0],[0,4],[0,-4]],np.float32),(3,1))
    elif moving and kind=='local_rotation':
        angle=.5;rotation=np.array([[np.cos(angle),-np.sin(angle)],[np.sin(angle),np.cos(angle)]])
        centre=patch.mean(axis=0)
        q[-12:]=(patch-centre)@rotation.T+centre+camera
    return p,q
