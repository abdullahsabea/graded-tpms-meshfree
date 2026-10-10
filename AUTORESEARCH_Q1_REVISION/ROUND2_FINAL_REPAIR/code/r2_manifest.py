"""ROUND2 manifest: SHA256 of every source artifact this correction round
reads, plus the new-input environment pins (docker digest, tool versions).
Writes results/MANIFEST_ROUND2.json. Read-only with respect to all sources.

Historical evidence is preserved in place; ROUND2 outputs never overwrite it.
"""
import hashlib
import json
import os
import platform
import subprocess
import sys
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
R2 = os.path.dirname(HERE)
WS = os.path.dirname(R2)                      # AUTORESEARCH_Q1_REVISION
REPO = os.path.dirname(WS)

SOURCES = [
    # PI audit
    "PI_AUDIT/PI_VERDICT.md",
    "PI_AUDIT/check_existing_evidence.py",
    # first-round state (frozen, read-only this round)
    "04_preregistered_plan.md",
    "experiments.tsv",
    "decisions.log",
    "FINAL_REPORT_FOR_PI.md",
    "claim_evidence_matrix.csv",
    "state.md",
    # first-round code (defects documented by the PI)
    "code/vgmm_common.py",
    "code/replay_pool.py",
    "code/regroup_exp04.py",
    "code/run_vgmm.py",
    "code/seed_sensitivity.py",
    "code/make_figures.py",
    "code/pilot_exp01.py",
    # first-round results (historical evidence)
    "results/pilot_exp01.json",
    "results/pool_replay.json",
    "results/pool_table.csv",
    "results/seed_final_fe_check.json",
    "results/seed_sensitivity.json",
    "results/vgmm_result.json",
    "logs/exp02_vgmm_run.log",
    # sources of truth in the repo
    "../research/n3/e3_fe_baseline.json",
    "../research/n3/e3_fe_baseline.py",
    "../research/n3/e3_conditional.py",
    "../research/n3/e3_cond.pt",
    "../research/n3/e3_coord_search.json",
    "../research/n3/paper_numbers.json",
    "../research/n3/e3_opt_history.json",
    "../research/n3/e3_opt_result.json",
    # manuscript base of the first revision round
    "manuscript/manuscript_revised.tex",
    "manuscript/references_verified.bib",
    "../SEP_PUBLICATION/ELSEVIER_UPLOAD_READY/manuscript/manuscript.tex",
    "../SEP_PUBLICATION/ELSEVIER_UPLOAD_READY/manuscript/references.bib",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    man = {
        "created_utc": now.isoformat(timespec="seconds"),
        "purpose": "ROUND2 source-manifest; historical artifacts are frozen "
                   "evidence and are only read",
        "platform": platform.platform(),
        "python": sys.version,
        "files": {},
        "environment": {},
    }
    for rel in SOURCES:
        p = os.path.normpath(os.path.join(WS, rel))
        man["files"][rel] = {
            "sha256": sha256(p),
            "bytes": os.path.getsize(p),
        }
    try:
        import numpy
        import scipy
        import torch
        import matplotlib
        man["environment"]["numpy"] = numpy.__version__
        man["environment"]["scipy"] = scipy.__version__
        man["environment"]["torch"] = torch.__version__
        man["environment"]["matplotlib"] = matplotlib.__version__
    except Exception as e:  # pragma: no cover
        man["environment"]["import_error"] = repr(e)
    try:
        out = subprocess.run(
            ["docker", "inspect", "--format",
             "{{range .RepoDigests}}{{.}}{{end}}",
             "simvia/code_aster:stable"],
            capture_output=True, text=True, timeout=60, check=True)
        man["environment"]["docker_image_digest"] = out.stdout.strip()
        man["environment"]["docker_image"] = "simvia/code_aster:stable"
    except Exception as e:  # pragma: no cover
        man["environment"]["docker_error"] = repr(e)
    dst = os.path.join(R2, "results", "MANIFEST_ROUND2.json")
    json.dump(man, open(dst, "w"), indent=2, sort_keys=True)
    print(f"wrote {dst} with {len(man['files'])} file hashes")
    for k, v in man["environment"].items():
        print(f"  env {k}: {v}")


if __name__ == "__main__":
    main()
