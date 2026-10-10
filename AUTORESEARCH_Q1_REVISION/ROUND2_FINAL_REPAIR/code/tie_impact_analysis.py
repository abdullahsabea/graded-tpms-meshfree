"""tie_impact_analysis: does the r2_arms.py:139 strict tie-policy fix
(``top_sc > incumbent_sc`` instead of ``top_val != incumbent_val``) change
any of the three frozen DEM-only-greedy trajectories (demonly11/12/13)?

Method (read-only, NO new FE simulations, NO writes to any frozen file):
  For each seed, this script deterministically replays the exact same
  proposal_demonly() trial computation r2_arms.py's run_arm() used to
  produce the frozen results/r2_arms/arm_demonly<seed>.json log (same
  scorer, same theta start, same sweep/mode order). At every step it
  computes top_sc and incumbent_sc from the trial set and evaluates BOTH
  decision rules on that same trial set:
    OLD:    move iff top_val != incumbent_val
    STRICT: move iff top_val != incumbent_val AND top_sc > incumbent_sc
  The OLD-policy replay is cross-checked against the frozen log's own
  recorded action/dem_pick at every step; a mismatch there would mean this
  replay is not faithful and the result below should not be trusted. Only
  the DEM (mesh-free) scorer is evaluated -- no FE solve, no Docker call,
  no file write to results/r2_arms/.
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import vg2_common as v2  # noqa: E402


def replay(seed):
    arm_path = os.path.join(R2, "results", "r2_arms", f"arm_demonly{seed}.json")
    frozen = json.load(open(arm_path, encoding="utf-8"))
    frozen_log = frozen["log"]

    scorer = v2.make_scorer(cloud_seed=seed)
    theta_old = [0.0] * v2.N_MODES
    theta_strict = [0.0] * v2.N_MODES

    steps = []
    old_matches_frozen = True
    diverged_at = None

    for i, entry in enumerate(frozen_log):
        s, m = entry["sweep"], entry["mode"]
        incumbent_val = float(theta_old[m])  # theta_old==theta_strict until first divergence
        incumbent_sc = None
        trials = []
        for cand in v2.GRID:
            tr = list(theta_old)
            tr[m] = float(cand)
            sh = v2.bisect_shift_discrete(64, tr)
            sc = scorer(tr, sh)
            if abs(float(cand) - incumbent_val) < 1e-9:
                incumbent_sc = sc
            trials.append((sc, float(cand), tr))
        trials.sort(key=lambda p: -p[0])
        top_sc, top_val, top_tr = trials[0]

        old_moves = (top_val != incumbent_val)
        strict_moves = (top_val != incumbent_val and incumbent_sc is not None
                         and top_sc > incumbent_sc)
        is_tie = (top_val != incumbent_val and incumbent_sc is not None
                  and top_sc == incumbent_sc)
        is_reversal = (top_val != incumbent_val and incumbent_sc is not None
                       and top_sc < incumbent_sc)

        frozen_action = entry["action"]
        frozen_old_moved = (frozen_action == "DEMMOVE")
        if old_moves != frozen_old_moved:
            old_matches_frozen = False

        if old_moves:
            theta_old[m] = top_val
        if strict_moves:
            theta_strict[m] = top_val

        step_diverges = (theta_old[m] != theta_strict[m])
        if step_diverges and diverged_at is None:
            diverged_at = i

        steps.append(dict(
            i=i, sweep=s, mode=m, incumbent_val=incumbent_val,
            top_val=top_val, top_sc=top_sc, incumbent_sc=incumbent_sc,
            old_moves=old_moves, strict_moves=strict_moves,
            is_exact_tie=is_tie, is_reversal=is_reversal,
            frozen_action=frozen_action, old_replay_matches_frozen=(old_moves == frozen_old_moved),
        ))

    return dict(
        seed=seed,
        n_steps=len(steps),
        old_replay_matches_frozen_log=old_matches_frozen,
        any_exact_tie=any(st["is_exact_tie"] for st in steps),
        any_reversal=any(st["is_reversal"] for st in steps),
        any_decision_divergence=any(st["old_moves"] != st["strict_moves"] for st in steps),
        diverged_at_step=diverged_at,
        theta_old_final=theta_old,
        theta_strict_final=theta_strict,
        theta_final_identical=(theta_old == theta_strict),
        frozen_theta_final=frozen["theta_final"],
        frozen_theta_final_matches_old_replay=(frozen["theta_final"] == theta_old),
        steps=steps,
    )


def main():
    results = {}
    for seed in (11, 12, 13):
        print(f"replaying demonly{seed} ...", flush=True)
        results[seed] = replay(seed)
        r = results[seed]
        print(f"  old_replay_matches_frozen_log={r['old_replay_matches_frozen_log']} "
              f"any_exact_tie={r['any_exact_tie']} any_reversal={r['any_reversal']} "
              f"any_decision_divergence={r['any_decision_divergence']} "
              f"theta_final_identical={r['theta_final_identical']}")

    out = {
        "method": __doc__,
        "per_seed_summary": {
            seed: {k: v for k, v in r.items() if k != "steps"}
            for seed, r in results.items()
        },
        "per_seed_steps": {seed: r["steps"] for seed, r in results.items()},
    }
    out_path = os.path.join(R2, "results", "tie_impact_analysis.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)

    log_path = os.path.join(R2, "logs", "tie_impact_analysis.log")
    with open(log_path, "w", encoding="utf-8") as f:
        f.write("tie_impact_analysis: replay of frozen demonly11/12/13 "
                "trajectories under OLD vs STRICT tie policy\n\n")
        for seed, r in results.items():
            f.write(f"seed {seed}:\n")
            for k in ("n_steps", "old_replay_matches_frozen_log", "any_exact_tie",
                      "any_reversal", "any_decision_divergence", "diverged_at_step",
                      "theta_final_identical", "frozen_theta_final_matches_old_replay"):
                f.write(f"  {k}: {r[k]}\n")
            f.write("\n")
    print(f"wrote {out_path}")
    print(f"wrote {log_path}")

    all_faithful = all(r["old_replay_matches_frozen_log"] for r in results.values())
    all_unaffected = all(r["theta_final_identical"] for r in results.values())
    if not all_faithful:
        print("WARNING: replay did not reproduce the frozen log for at least "
              "one seed -- do not trust the divergence conclusion below "
              "without investigating this mismatch first.")
        return 2
    print(f"All three frozen DEM-only trajectories replay-faithful: {all_faithful}")
    print(f"All three frozen DEM-only trajectories unaffected by the strict "
          f"tie-policy fix (theta_final identical old vs strict): {all_unaffected}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
