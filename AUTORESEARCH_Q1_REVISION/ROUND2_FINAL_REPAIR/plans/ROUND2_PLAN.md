# ROUND2_PI_CORRECTION prospective plan (local, written before outcome runs)

**Created:** 2026-09-13 (UTC timestamp recorded with the hash in
`results/decisions_round2.log`, entry PLAN-FROST-2A). This is a LOCAL
prospective plan for corrective controlled comparisons. It is NOT an
externally registered study and must not be described as preregistration in
that sense. It is written and hashed BEFORE any new outcome-producing run of
this round. The first-round plan (`../../04_preregistered_plan.md`) is
preserved unchanged; its deviations are listed in Appendix D.

## 1. Motivation and scope

The PI audit (PI_VERDICT.md, 2026-09-13) confirmed the VG-MM confirmation
result (+5.558% at 96^3, 26 calls) against raw solver logs, and reopened:
deterministic reporting defects (budget axis, denominators, selected-proposal
scores, replay grouping), confounded seed inference, inconsistent cost
accounting, reproduction hygiene, missing attribution controls, and
unsupported runtime/provenance statements. This plan freezes the corrective
computations. All historical artifacts are read-only; every ROUND2 output is
written under `AUTORESEARCH_Q1_REVISION/ROUND2_PI_CORRECTION/`.

## 2. Corrective (non-outcome) computations — Stage A

These re-derive bookkeeping from existing caches; NO new FE solves and no
effect on the controlled-outcome arms below:

- A1 **Fixed replay producer** (`code/r2_replay.py`): reconstructs the
  archived FE-search pool AND its 24 per-scan groups in ONE pass, using
  `entry["pick"]` at each step (defect: first-round `replay_pool.py` used the
  stale last-loop value and needed `regroup_exp04.py` to patch the JSON).
  Output goes to `results/r2_pool_replay.json` (new file; historical
  `results/pool_replay.json` is never overwritten).
- A2 **Tie-aware rank statistics** via `scipy.stats.spearmanr/kendalltau`
  (library implementations handle ties; the hand-rolled ranks did not). We
  additionally RECORD (i) exact score ties, (ii) practical near-ties defined
  as adjacent-rank |Δscore| < 1e-6 (DEM) or |ΔC_FE| < 1e-9 (FE), and we
  distinguish "different IDs selected" from "material ranking loss"
  (a discordant pick whose FE values differ by < 0.05 pp of gain is recorded
  as ID-level disagreement only).
- A3 **Pool reconciliation**: enumerate every file in `research/n3/febase/`,
  recompute required keys for the archived search (192 unique search designs
  incl. uniform64, + uniform96 + winner96 = 194 required), and IDENTIFY the
  extra cached file(s) by reconstructing the query that produced them
  (candidates: exploratory solves made during the first-round pilot's initial
  choice). No guessing: each extra key must be explained by a reproduced
  (N, theta, shift) triple and its provenance recorded.
- A4 **Selected-proposal score correction**: for the historical VG-MM run we
  re-derive, from the stored `dem_rank_top3` plus the selection rule, the DEM
  score of the ACTUALLY SELECTED non-incumbent proposal, recorded separately
  from the overall top score and the incumbent score. The historical JSON is
  not edited; the corrected derivation is written to
  `results/r2_vgmm_historical_corrections.json`.
- A5 **Cache-parser hardening** (in new common code `code/vg2_common.py`):
  every cache read requires (i) `DIAGNOSTIC JOB : OK` in the `.mess`, (ii) a
  parsable `C1111_ENERGY`, (iii) provenance check — the cached `.mail` mesh,
  if present, must hash-identically to a rebuild from the query triple (mesh
  determinism), else the entry is rejected and treated as a miss. Docker
  image digest is pinned:
  `simvia/code_aster@sha256:d8d19ea91989eac0d38195bc5795c54c69f530f7196f53d67697ffa57c9106d5`.
- A6 **Seed-endpoint standalone verification command**
  (`code/r2_seed_endpoint_check.py`): one exact command that re-verifies the
  first-round seed-12/13 endpoint FE values from raw `.mess` files and
  recomputes gains with explicit denominators.
- A7 **Ledger hygiene**: `results/experiments_round2.tsv` (fixed schema,
  every row = 12 tab-separated fields, header validated by test) and
  `results/decisions_round2.log` (append-only, REAL UTC timestamps from the
  system clock at write time). Historical corrections are logged NOW; no
  backdating. The first-round `experiments.tsv` rows with 13 fields are
  preserved as-is (historical) and copied with corrected schema into the
  ROUND2 ledger marked `schema_fix`.
- A8 **Historical timing recovery**: EXP-02 wall time from
  `logs/exp02_vgmm_run.log` (840 s cumulative driver time; sequential
  checkpoints; single sequential confirmation). Archived full-FE search wall
  time: NOT recoverable from any stored record -> reported as "unavailable"
  (the first-round "half an hour / six-fold parallelism" and "0.9 h /
  sixfold-parallel confirm" statements are withdrawn). New runs record
  per-call wall times split by phase.

## 3. Controlled comparison arms — Stage B (outcome-producing)

All arms share EXACTLY: initialization theta = 0 (12 coefficients), mode
order [(1,0,0),(0,1,0),(0,0,1),(1,1,0),(1,0,1),(0,1,1)] (cos,sin pairs),
2 sweeps x 12 modes, trial grid `linspace(-0.22,0.22,9)`, bounds
t in [0.12,0.55], discrete-Vf bisection to 0.19328 (28 iterations),
KUBC energy basis C1111_ENERGY, search grid 64^3, confirmation 96^3,
FE-acceptance rule "accept iff candidate FE value STRICTLY exceeds the
FE-best incumbent", and evaluation budget of 26 counted calls
(1 uniform baseline + 24 checkpoint proposals + 1 confirm96). Cached hits
count as calls with equal accounting; no arm's PROPOSAL function may access
FE values of candidates it has not queried (enforced by construction:
proposal functions receive only the policy's own information state).

### Arms

- **B-VGMM(c)** c in {11,12,13} — original proposal rule: rank the 9 trials
  by the frozen conditional-DEM soft score (fixed 50k cloud, cloud seed c);
  propose the highest-DE-scored trial whose coefficient differs from the
  incumbent's. c=11 is the HISTORICAL run (reused unchanged from
  `../../results/vgmm_result.json`, preserving its recorded counts
  26 calls / 20 new solves; no rerun). c=12,13 are new runs.
- **B-RAND(r)** r in {11,12,13} — uniformly random non-incumbent grid
  proposal: `numpy.random.default_rng(r)`, at each checkpoint sample
  uniformly from the 8 grid values different from the incumbent's current
  value (the incumbent value is always on-grid by construction). Same
  FE-acceptance rule, same budget.
- **B-DET** (unseeded) — deterministic inexpensive proposal: fixed cyclic
  order over the 8 non-incumbent grid values
  [-0.22, +0.22, -0.165, +0.165, -0.11, +0.11, -0.055, +0.055]; at
  checkpoint k (k = 2*12 index, 0-based) propose `order[k mod 8]`; if that
  value equals the incumbent's current value, take the next value in the
  cycle that differs. No surrogate, no RNG.
- **B-FULLFE26** — the archived full-FE search truncated at the matched
  26-call budget (NO new solves; from the A1 replay). Accounting frozen:
  unique-evaluation order with deduplication (each new distinct design
  counts once, repeats are free); frontier value = best FE among the first
  26 unique designs in query order. Because the archived search evaluated
  scan batches of 10 in parallel, we ALSO report the batch-complete frontier
  at 25 unique designs (3 complete scans) and explicitly mark that call 26
  falls inside incomplete scan 4. Baseline/confirm conventions identical.
- **B-DEMONLY(c)** c in {11,12,13} — faithful DEM-only greedy: argmax over
  ALL 9 trials INCLUDING the incumbent; move iff the argmax differs from the
  incumbent AND its DEM score is strictly higher (never forces a
  lower-scoring move). No FE in the loop; the FINAL design is then FE-checked
  at 64^3 and 96^3 (2 calls, outside the 26-call budget, reported
  separately as an endpoint audit). Note: first-round `seed_sensitivity.py`
  forced moves even when the incumbent scored highest — that defect is what
  this arm fixes.

### Seed taxonomy (declared)

- Model-training seed: SINGLE frozen checkpoint `e3_cond.pt` for every arm
  (not varied; declared limitation — no retraining within this budget).
- Integration-cloud seed c: affects only DEM scoring (B-VGMM, B-DEMONLY).
- Random-proposal seed r: affects only B-RAND's RNG.
Never compare across different policy families as evidence of seed effects.

### Frozen common state collection for quadrature isolation

The 192-design reconstructed pool (A1) with fixed (theta, shift) triples,
plus the 24 archived per-scan candidate groups. For clouds c in {11,12,13}:
Spearman/Kendall between cloud DEM score vectors, group top-1 agreement
between clouds, and each cloud's OWN uniform-design DEM denominator
(score of theta=0 under cloud c) for normalized-gain reporting. No FE
involved; purely isolates quadrature effects.

## 4. Endpoints, metrics, and frozen thresholds

- **Primary endpoint (matched-budget verified gain):**
  `G26 = 100*(C_inc_final_64 / 0.10528125601 - 1)` evaluated at exactly 26
  counted calls per arm (uniform64 baseline value shared and counted
  identically for every arm).
- **Predeclared practical difference margin:** delta = 1.0 percentage point
  (pp) of verified gain. Justification (fixed before outcomes): the archived
  verification ladder's per-grid scatter for graded designs is ~0.35 pp
  half-range and the band-restriction effect size is ~1.6 pp; 1.0 pp sits
  above ladder scatter and below the smallest policy effect the first round
  considered meaningful.
- Secondary endpoints (all reported): G_confirm96 at call 26; acceptance
  counts; harmful rejected proposals (queried proposals with FE gain
  < -5 pp); best-so-far trajectory (per call); per-phase runtime (DEM
  scoring s, meshing s, FE solve s, cached replay s, total); endpoint
  variability across each family's seeds; RAW query count vs unique-problem
  count vs new-solve count, reported for every arm.
- **Frozen outcome branches** on the primary endpoint
  (VG family = {B-VGMM(11)} u new {12,13}; RAND family = {B-RAND(11,12,13)};
  DET = B-DET):
  - **B1 "DEM guidance useful here":** min(VG) >= max(RAND) + delta AND
    min(VG) >= DET + delta.
  - **B2 "statistically indistinguishable at this scale":** all
    cross-family differences within delta.
  - **B3 "controls better":** max(RAND or DET) >= min(VG) + delta.
  - **B4 INCONCLUSIVE:** budget exhaustion or harness failure in any family.
  - Mixed outcomes are reported by branch of each pairwise comparison; no
    post-hoc threshold movement. A three-run pilot is descriptive; NO
    population-level inference, no confidence bands, no significance stars.
  - Interpretation language (frozen): B1 -> "DEM ranking added value beyond
    FE acceptance on this problem"; B2 -> "FE acceptance, not DEM ranking,
    drives the observed gains at this budget"; B3 -> same as B2 with the
    stronger note that a cheaper rule beat the learned ranking.
- **Scope limits (frozen):** monotonicity holds ONLY for the same-grid
  accepted FE objective. NO claim of universal safety, continuum
  certification, or finer-grid monotonicity without explicit verification.
  Lower-cost/lower-gain methods are never called "dominated"; gain and cost
  are reported separately.

## 5. Budget and feasibility (fixed before runs)

- Hard caps: <= 200 NEW FE solves this round; <= 4 h wall clock of new FE
  computation; measured single-desktop sequential N64 solve ~23-40 s
  (pilot P3 23.4 s solve; EXP-02 log shows ~36 s per checkpoint including
  meshing), N96 ~47 s.
- Estimated need: B-VGMM(12) <= 26 calls (<= 26 new), B-VGMM(13) <= 26,
  B-RAND x3 <= 78, B-DET <= 26, B-DEMONLY x3 <= 6 endpoint solves,
  contingency/retries <= 12. Upper bound 200. If the cap is hit before all
  arms complete, the missing arm is reported as INCOMPLETE REPLICATION —
  the seed set is NOT reduced and no arm is substituted.
- No publication, deposits, external-model uploads, paid services, or
  destructive actions. Frozen packages untouched.

## 6. Exclusion rules (frozen)

- FE solve failure: 1 retry; second failure -> arm marked INCONCLUSIVE
  (logs preserved).
- Cache `.mess` failing A5 checks -> treated as a miss and re-solved (counted
  as a new solve).
- Bisection failure / degenerate discrete Vf -> candidate excluded with a
  logged row; NOT silently dropped.
- No candidate or result may be excluded post hoc for its value.
- Arms failing mid-run are preserved with partial trajectories.

## 7. Planned outputs

- `results/r2_pool_replay.json` (A1/A2/A3), `results/r2_arms/*.json` (one
  per arm, append-safe unique names), `results/r2_seed_endpoint_check.json`,
  `results/experiments_round2.tsv`, `results/decisions_round2.log`,
  `results/r2_quadrature_isolation.json`, `results/r2_accounting.json`
  (common-budget table, raw/unique/new counts, runtimes),
  figures R1-R5 under `figures/`, revised manuscript under `manuscript/`,
  tests under `tests/`, this plan + hash under `plans/`.

## Appendix D: deviations from the first-round plan (04_preregistered_plan.md)

1. Budget raised from <=40 new solves to <=200 (the first round's controls
   were missing; the PI mandated matched-budget controls; feasibility
   re-derived from the recorded ~23 s N64 pilot).
2. Seed plan replaced: first round compared DEM-only seed12/13 forced-move
   paths against seed-11 VG-MM (confounded; withdrawn). This round runs the
   SAME policy across seeds and isolates quadrature on frozen states.
3. Primary endpoint of the first round (G_confirm96 vs thresholds incl.
   a self-assigned PASS band) is DEMOTED to a secondary endpoint; the
   self-assigned PASS/STRONG thresholds are not reused as external
   validation. The new primary endpoint is the matched-budget G26 family
   comparison with the predeclared delta margin.
4. Confirmation double counting fixed: the first round's "20 new ... plus
   confirmation" phrasing (confirmation already inside the 20) and the
   budget-plot axis (scan index) are replaced by the Section 3 accounting.
5. Runtime claims not derivable from records are withdrawn rather than
   re-estimated.

## Hash

SHA256 of this file recorded in `results/decisions_round2.log` at freeze
time (entry PLAN-FROST-2A). Any later edit invalidates the hash and must be
logged as a post-outcome change.
