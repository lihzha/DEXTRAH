# Reward and Success Comparison

This directory logs the current comparison between the known-good no-tracking
Franka cube baseline and the first five-seed RL + trajectory-tracking-loss
sweep.

## Runs

| Method | Seeds | Training run source |
| --- | --- | --- |
| No tracking baseline | `1781139395` | `/tmp/franka_compare_tracking_vs_baseline/baseline` |
| Tracking loss | `1,2,3,4,5` | `/tmp/franka_compare_tracking_vs_baseline/tracking/seed*` |

The no-tracking curve is a single historical-seed run. The tracking curve shows
all five explicit base seeds and their common-epoch mean.

## Outputs

| File | Contents |
| --- | --- |
| `reward_curve_comparison.svg` | TensorBoard `rewards/iter` curve: no-tracking baseline vs tracking seeds and mean. |
| `success_rate_curve_comparison.svg` | TensorBoard `Episode/cube_success_rate` curve: no-tracking baseline vs tracking seeds and mean. |
| `eval_success_comparison.svg` | Existing eval success comparison with tracking seed points. |
| `training_curves.csv` | Per-epoch reward and training success-rate values for all runs. |
| `training_summary.csv` | Final, best, and last-20-window aggregate reward/success summaries. |
| `reward_terms_summary.csv` | Final, best, and last-20-window per-term reward summaries. |
| `eval_success_summary.csv` | Existing eval success metrics and definitions. |
| `manifest.json` | Source artifact manifest. |

## Key Numbers

| Method | Final train reward | Last-20 train reward | Final train success | Last-20 train success | Primary eval success |
| --- | ---: | ---: | ---: | ---: | ---: |
| No tracking baseline | `13044.795` | `13067.345` | `0.819` | `0.828` | `0.948` |
| Tracking loss mean, seeds 1-5 | `8515.849 +/- 4789.768` | `8427.648 +/- 4719.371` | `0.474 +/- 0.385` | `0.451 +/- 0.370` | `0.600` |

For eval success, the baseline value is `eval_success_rate` over the existing
1024-env first-attempt eval. The tracking value is the mean of per-seed
`success_ever_rate` over the existing five 16-env pure-policy evals. The eval
definitions are therefore not identical; use `eval_success_summary.csv` for the
raw definitions and occupancy metrics.

Reward scale is also not a pure outcome comparison because the tracking method
adds tracking reward terms. The success-rate curves and eval success table are
the cleaner behavioral comparison.
