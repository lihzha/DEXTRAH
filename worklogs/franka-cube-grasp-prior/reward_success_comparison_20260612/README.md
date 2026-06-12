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
| `combined_reward_mean_std.svg` | Combined aggregate reward mean +/- std: no-prior baseline, grasp pose prior, and tracking loss. |
| `combined_success_rate_mean_std.svg` | Combined training success-rate mean +/- std: no-prior baseline, grasp pose prior, and tracking loss. |
| `training_curves.csv` | Per-epoch reward and training success-rate values for all runs. |
| `training_summary.csv` | Final, best, and last-20-window aggregate reward/success summaries. |
| `reward_terms_summary.csv` | Final, best, and last-20-window per-term reward summaries. |
| `eval_success_summary.csv` | Existing eval success metrics and definitions. |
| `combined_reward_plot_means.csv` | Combined reward means/stds used by `combined_reward_mean_std.svg`. |
| `combined_success_rate_plot_means.csv` | Combined success-rate means/stds used by `combined_success_rate_mean_std.svg`. |
| `combined_plot_manifest.json` | Source manifest for the combined plots. |
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

## Combined Seed-Sweep Comparison

The combined plots use the seed-sweep files in
`/home/lzha/code/DEXTRAH/cluster_results/a1001/franka_cube_seed_sweep600_c7e66a0_20260612_092951`.
Rows named as previous baselines are excluded.

For reward, all three methods are plotted only over epochs where seeds `1..5`
are all present for that method:

| Method | Reward epochs | Last mean +/- std |
| --- | ---: | ---: |
| No prior baseline | `1..567` | `4293.220 +/- 4467.953` |
| Grasp pose prior | `1..589` | `13825.325 +/- 310.439` |
| Tracking loss | `1..571` | `8630.591 +/- 4811.139` |

For training success rate:

| Method | Success epochs | Last mean +/- std |
| --- | ---: | ---: |
| No prior baseline | `1..600` | `0.179 +/- 0.356` |
| Grasp pose prior | `1..600` | `0.865 +/- 0.030` |
| Tracking loss | `1..571` | `0.475 +/- 0.387` |

Visual inspection notes:
- Existing tracking-vs-single-baseline plots render correctly, but they only
  compare tracking loss against one historical no-tracking seed.
- The combined reward plot is visually coherent after restricting reward to
  strict five-seed coverage. Without that restriction, the supplied reward mean
  CSV has late rows with `n < 5` for the seed-sweep methods.
- The combined success-rate plot shows the same ranking as the eval summary:
  grasp pose prior is clearly strongest; tracking loss improves over no-prior
  on training success but remains unstable and below grasp pose prior.
