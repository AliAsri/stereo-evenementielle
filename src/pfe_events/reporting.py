"""Historical timing report schemas; kept distinct for output compatibility."""
import numpy as np


def activity_distribution(values):
    a = np.asarray(values, dtype=float)
    return {"count": len(a), "mean": float(a.mean()), "median": float(np.median(a)),
            "p95": float(np.percentile(a, 95)), "max": float(a.max())}


def paced_distribution(values):
    return {'count':len(values),'mean':float(np.mean(values)),
            'median':float(np.median(values)),'p95':float(np.percentile(values,95)),
            'p99':float(np.percentile(values,99)),'max':float(np.max(values))} if values else None


def adaptive_distribution(values):
    return {'count': len(values), 'median': float(np.median(values)),
            'p95': float(np.percentile(values,95)), 'max': float(np.max(values))} if values else None


def rigid_distribution(values):
    return dict(count=len(values),median=float(np.median(values)),p95=float(np.percentile(values,95))) if values else None
