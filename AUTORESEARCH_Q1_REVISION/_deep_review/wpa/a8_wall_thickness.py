"""WP-A8: physical gyroid-sheet wall thickness (mm) at a 15 mm cell.
Sheet |F(kx)| <= t, F = sin x cos y + sin y cos z + sin z cos x, k = 2*pi/L.
Thickness at a mid-surface point = distance along the normal between F=-t and F=+t."""
import numpy as np
from scipy.optimize import brentq
L = 15.0; k = 2*np.pi/L
F = lambda p: np.sin(p[0])*np.cos(p[1]) + np.sin(p[1])*np.cos(p[2]) + np.sin(p[2])*np.cos(p[0])
def G(p):
    x, y, z = p
    return np.array([np.cos(x)*np.cos(y) - np.sin(z)*np.sin(x),
                     np.cos(y)*np.cos(z) - np.sin(x)*np.sin(y),
                     np.cos(z)*np.cos(x) - np.sin(y)*np.sin(z)])
rng = np.random.default_rng(0)
pts = []
while len(pts) < 4000:                      # Newton-project random points onto F=0
    p = rng.uniform(0, 2*np.pi, 3)
    for _ in range(30):
        g = G(p); f = F(p)
        p = p - f*g/(g@g + 1e-12)
        if abs(f) < 1e-12: break
    if abs(F(p)) < 1e-10 and np.linalg.norm(G(p)) > 1e-3: pts.append(p)
pts = np.array(pts)
# area-weighting: random projection is not area-uniform; also report unweighted
out = {}
for t in [0.12, 0.20, 0.30, 0.45, 0.55]:
    w = []
    for p in pts:
        n = G(p)/np.linalg.norm(G(p))
        s = []
        for sgn, lev in [(+1, None), (-1, None)]:
            f0 = lambda a: abs(F(p + sgn*a*n)) - t
            a_hi = 0.05
            while f0(a_hi) < 0 and a_hi < 2.0: a_hi *= 1.3
            s.append(brentq(f0, 0, a_hi) if f0(a_hi) > 0 else np.nan)
        w.append(sum(s)/k)                  # radians -> mm
    w = np.array(w); w = w[np.isfinite(w)]
    out[t] = w
    print(f"t={t:.2f}: wall [mm] min {w.min():.2f}  p5 {np.percentile(w,5):.2f}  median {np.median(w):.2f}  p95 {np.percentile(w,95):.2f}  max {w.max():.2f}  (linear 2t/|gradF| est. median {np.median(2*t/np.linalg.norm(np.array([G(p) for p in pts]),axis=1))/k:.2f})")
