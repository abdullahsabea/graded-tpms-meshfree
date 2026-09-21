# Reproducibility guide

## Fast, deterministic checks

`python validation/verify_experiment_stats.py` reads the eight archived Instron exports, fits the documented 150--600 N loading-window slopes, and writes `validation/table8_results.json`. It also records the primary ratio interval, the rate-mismatch sensitivity excluding U1, mass sensitivities, and the predefined window sweep.

`python paper/make_fig16_experimental.py` regenerates the experimental figure from those CSVs and JSON assertions. The U/O coupon drawings are schematic keys only; they are not measured geometries and are not to scale.

## Research-scale workflows

`research/` contains the analytic geometry, DEM, optimization, and Code_Aster FE support workflows. Their runtime depends on mesh resolution, trained-model availability, and local Code_Aster configuration. They are intentionally preserved as research code rather than presented as a one-command benchmark.

## Interpretation boundary

The physical series contains four specimens per group from one build. U1 ran at approximately 1 mm/min; the other seven records ran at approximately 3 mm/min. The leave-U1-out calculation is a transparent sensitivity analysis, not a correction for the protocol deviation. Cross-build replication, rate-matched testing, and dimensional metrology remain necessary for general physical claims.
