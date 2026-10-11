"""Two-view 3D reference scenes. No event sensor or tracking simulation."""
import cv2
import numpy as np

KINDS = ('static', 'camera_translation', 'camera_rotation', 'object_translation',
         'combined', 'object_rotation', 'missing_depth', 'biased_near_depth',
         'dominant_moving_layer')


def project(points, intrinsic):
    pixels = points @ intrinsic.T
    return pixels[:, :2] / pixels[:, 2, None]


def make_scene(kind, seed=0, noise_px=0.):
    if kind not in KINDS or not np.isfinite(noise_px) or noise_px < 0:
        raise ValueError('Unknown scene or invalid noise')
    rng = np.random.default_rng(seed)
    k = np.array([[500., 0, 320], [0, 500, 240], [0, 0, 1]])
    x, y = np.meshgrid(np.linspace(65, 575, 12), np.linspace(55, 425, 9))
    background = np.column_stack((x.ravel(), y.ravel()))
    z = np.tile([6., 12., 24.], 36)
    x, y = np.meshgrid(np.linspace(290, 350, 4), np.linspace(180, 260, 4))
    patch = np.column_stack((x.ravel(), y.ravel()))
    p = np.vstack((background, patch))
    depth = np.r_[z, np.full(len(patch), 5.)]
    xyz = np.column_stack(((p[:, 0]-320)/500*depth, (p[:, 1]-240)/500*depth, depth))
    moving = np.zeros(len(p), bool)
    moved = xyz.copy()
    if kind in ('object_translation', 'combined'):
        moving[-len(patch):] = True
        moved[moving, 0] += .08
    if kind == 'object_rotation':
        moving[-len(patch):] = True
        centre = xyz[moving].mean(axis=0)
        local_rotation = cv2.Rodrigues(np.array([0., 0., .35]))[0]
        moved[moving] = (xyz[moving]-centre) @ local_rotation.T + centre
    if kind == 'dominant_moving_layer':
        moving[:len(background)] = True
        moved[moving, 0] += .16
    translation = np.array([-.08, 0., 0.]) if kind in (
        'camera_translation', 'combined', 'missing_depth', 'biased_near_depth',
        'dominant_moving_layer') else np.zeros(3)
    rotation_vector = np.array([.003, .012, -.004]) if kind in ('camera_rotation', 'combined') else np.zeros(3)
    rotation = cv2.Rodrigues(rotation_vector)[0]
    q_exact = project(moved @ rotation.T + translation, k)
    q = q_exact + rng.normal(0, noise_px, q_exact.shape)
    input_depth = depth.copy()
    if kind == 'missing_depth':
        input_depth[:] = np.nan
        input_depth[:10] = depth[:10]
    if kind == 'biased_near_depth':
        input_depth[-len(patch):] *= 3
    transform = np.eye(4)
    transform[:3, :3], transform[:3, 3] = rotation, translation
    return dict(previous=p, current=q, depth_m=input_depth, true_depth_m=depth,
                intrinsic=k, moving=moving, transform=transform, kind=kind,
                noise_px=noise_px, seed=seed, previous_us=0, current_us=20000)
