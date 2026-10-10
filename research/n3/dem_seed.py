"""Training-seed study for the single-thickness gyroid DEM (t = 0.30).

Same architecture, loss, optimizer schedule and float64 audit as dem_gyroid.py;
the only change is the torch seed (Fourier-feature matrix B and network
initialization) and the collocation-sampling stream, trained in one run.

    python dem_seed.py <seed> [adam_iters=20000]
Writes n3_dem_seed<seed>.json.
"""
import json
import os
import sys
import time

import numpy as np
import torch

sys.argv = [sys.argv[0], "1", "0.3"] + sys.argv[1:]  # dem_gyroid reads argv[2] as t
import dem_gyroid as dg  # noqa: E402

SEED = int(sys.argv[3])
ITERS = int(sys.argv[4]) if len(sys.argv) > 4 else 20000
torch.set_num_threads(int(os.environ.get("DEM_THREADS", "12")))


def main():
    torch.set_default_dtype(torch.float32)
    torch.manual_seed(SEED)
    model = dg.make_model()
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)
    t0 = time.time()
    for it in range(ITERS):
        opt.zero_grad()
        pts = dg.sample_solid(6000, seed=SEED * 1_000_003 + it)
        U = dg.strain_energy(model, pts).mean() * dg.V_SOLID
        U.backward()
        opt.step()
        if it % 1000 == 0 or it == ITERS - 1:
            print(f"seed {SEED} it {it:6d} C1111={2 * float(U) / dg.EPS**2:.4f} ({time.time() - t0:.0f}s)", flush=True)
    fixed = dg.sample_solid(60_000, seed=999)
    opt2 = torch.optim.LBFGS(model.parameters(), max_iter=80, tolerance_grad=1e-10,
                             tolerance_change=1e-13, history_size=10, line_search_fn="strong_wolfe")

    def closure():
        opt2.zero_grad()
        U = dg.strain_energy(model, fixed).mean() * dg.V_SOLID
        U.backward()
        return U
    opt2.step(closure)
    torch.save(model.state_dict(), os.path.join(dg.HERE, f"dem_gyroid_seed{SEED}.pt"))

    torch.set_default_dtype(torch.float64)
    m64 = dg.make_model()
    m64.load_state_dict({k: v.double() for k, v in model.state_dict().items()})
    d = torch.cat([dg.strain_energy(m64, dg.sample_solid(20_000, seed=1000 + s).double()) for s in range(6)])
    U64 = d.mean().item() * dg.V_SOLID
    se = d.std().item() / np.sqrt(len(d)) * dg.V_SOLID
    out = dict(seed=SEED, adam_iters=ITERS, C1111_dem=2 * U64 / dg.EPS**2, C1111_se=2 * se / dg.EPS**2,
               V_solid=dg.V_SOLID, wall_s=round(time.time() - t0, 1))
    json.dump(out, open(os.path.join(dg.HERE, f"n3_dem_seed{SEED}.json"), "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    main()
