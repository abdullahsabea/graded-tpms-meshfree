"""WP-A1 check: volume fraction of solid pieces that are disconnected inside
the unit cell (connected only through the periodic images), per design."""
import json
import numpy as np
from scipy import ndimage
from make_conforming_mesh import F, t_field
n = 320
g = (np.arange(n) + 0.5) / n
X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
out = {}
for d in ["uniform", "printable", "vgmm", "fullfe", "graded"]:
    solid = np.abs(F(X, Y, Z)) <= t_field(d)(X, Y, Z)
    lab, nc = ndimage.label(solid)
    sizes = np.bincount(lab.ravel())[1:]
    big = sizes.max()
    small = sizes.sum() - big
    out[d] = dict(n_components=int(nc), solid_vf=float(solid.mean()), corner_vf=float(small / solid.size),
                  corner_share_of_solid=float(small / sizes.sum()))
    print(d, out[d])
json.dump(out, open("corner_pieces.json", "w"), indent=1)
