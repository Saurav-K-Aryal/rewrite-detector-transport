# T12 C synthetic two channel audit

## Paste ready text

With known synthetic calibration and one percent false positives, two channels estimated a marked fraction of 0.5 with 95 percent interval width at most 0.04 in at least 95 percent of replicates using 100,000 to 50,000,000 queries across four strengths, while one channel left fraction unidentified.

## Table

| Strength | TPR channel 1 and 2 | Queries | Coverage with MC 95% CI | Width at most .04 with MC 95% CI |
|---:|---:|---:|---:|---:|
| 0.75 | 75.25%, 56.69% | 100,000 | 100.00% [99.96, 100.00] | 100.00% [99.96, 100.00] |
| 0.5 | 50.50%, 25.75% | 200,000 | 99.95% [99.88, 99.98] | 100.00% [99.96, 100.00] |
| 0.25 | 25.75%, 7.19% | 500,000 | 99.89% [99.80, 99.95] | 100.00% [99.96, 100.00] |
| 0.05 | 5.95%, 1.25% | 50,000,000 | 99.08% [98.87, 99.26] | 100.00% [99.96, 100.00] |


## Limits and what was not established

Each table row uses 10000 independent confirmation replicates at marked fraction 0.5. Sensitivities are stipulated response curves, not measurements on real 50 token outputs. Calibration is known exactly and query outputs are independent. Both channels observe each query and share its latent mark, requiring two detector evaluations per query. Marginal exact intervals with a union bound remain valid under this within query dependence. Width at most 0.04 gives half width at most 0.02 around the reported interval midpoint. No precision guarantee is uniform near zero marking fraction or zero strength. Monte Carlo intervals describe simulation uncertainty. Empty projected confidence sets receive a flagged conservative [0,1] fallback. The candidate query grid does not identify the exact minimum sample size. Execution failures remain recorded rather than becoming simulated successes. No provider or actual watermark implementation was audited.

## Run record

```json
{
  "label": "Synthetic oracle-calibrated channels, not observed watermark performance on 50-token text",
  "one_channel_nonidentification": {
    "q1": 0.2575,
    "rho_times_theta": 0.25,
    "compatible_rho_interval": [
      0.25,
      1
    ],
    "examples_rho_theta": [
      [
        0.25,
        1
      ],
      [
        0.5,
        0.5
      ],
      [
        1,
        0.25
      ]
    ],
    "interpretation": "Even infinitely many first-channel queries cannot distinguish these parameter pairs"
  },
  "two_channel_inverse": {
    "a": "(q1-f)/(1-f)",
    "b": "(q2-f)/(1-f)",
    "theta": "b/a",
    "rho": "a*a/b",
    "jacobian_determinant": "(1-f)^2*rho*theta^2",
    "singularities": "rho=0 or theta=0"
  },
  "failures": [],
  "planned_selection_cells": 192,
  "planned_confirmation_cells": 12,
  "wall_seconds": 9.688548208010616,
  "finished_utc": "2026-11-18T19:27:28.360804+00:00",
  "confirmation": [
    {
      "rho": 0.1,
      "theta": 0.05,
      "fpr_both": 0.01,
      "sensitivity_1": 0.059500000000000004,
      "sensitivity_2": 0.012475,
      "queries": 50000000,
      "detector_evaluations": 100000000,
      "replicates": 10000,
      "coverage": 0.9869,
      "coverage_mc95": [
        0.9844740528077613,
        0.9890358615177594
      ],
      "precision_probability": 0.995,
      "precision_mc95": [
        0.9934133735709201,
        0.9962866938204445
      ],
      "mean_interval_width": 0.02964778078364342,
      "median_interval_width": 0.029358247528047776,
      "p95_interval_width": 0.03557564121076508,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.97496672625,
        0.014785773750000002,
        0.010083273750000002,
        0.00016422625000000004
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.1,
      "theta": 0.25,
      "fpr_both": 0.01,
      "sensitivity_1": 0.2575,
      "sensitivity_2": 0.071875,
      "queries": 500000,
      "detector_evaluations": 1000000,
      "replicates": 10000,
      "coverage": 0.9989,
      "coverage_mc95": [
        0.9980326505194581,
        0.9994507601153076
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.022475384202830226,
      "median_interval_width": 0.02243747865093463,
      "p95_interval_width": 0.0242020944613777,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.95100328125,
        0.03280921875000001,
        0.014246718750000002,
        0.00194078125
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.1,
      "theta": 0.5,
      "fpr_both": 0.01,
      "sensitivity_1": 0.505,
      "sensitivity_2": 0.2575,
      "queries": 50000,
      "detector_evaluations": 100000,
      "replicates": 10000,
      "coverage": 0.9995,
      "coverage_mc95": [
        0.9988335557909334,
        0.9998376320658011
      ],
      "precision_probability": 0.999,
      "precision_mc95": [
        0.9981617358657894,
        0.9995203602762289
      ],
      "mean_interval_width": 0.034375453751751536,
      "median_interval_width": 0.0343419909654548,
      "p95_interval_width": 0.03714792576384704,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.9188437500000001,
        0.04640625,
        0.021656250000000002,
        0.013093750000000001
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.1,
      "theta": 0.75,
      "fpr_both": 0.01,
      "sensitivity_1": 0.7525,
      "sensitivity_2": 0.566875,
      "queries": 50000,
      "detector_evaluations": 100000,
      "replicates": 10000,
      "coverage": 1.0,
      "coverage_mc95": [
        0.9996311800853812,
        1.0
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.02406815462628391,
      "median_interval_width": 0.024071001605651725,
      "p95_interval_width": 0.025051419330792787,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.89280984375,
        0.04150265625,
        0.022940156250000003,
        0.04274734375
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.5,
      "theta": 0.05,
      "fpr_both": 0.01,
      "sensitivity_1": 0.059500000000000004,
      "sensitivity_2": 0.012475,
      "queries": 50000000,
      "detector_evaluations": 100000000,
      "replicates": 10000,
      "coverage": 0.9908,
      "coverage_mc95": [
        0.9887287859255516,
        0.9925772403259312
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.031727145391972196,
      "median_interval_width": 0.03172112885935047,
      "p95_interval_width": 0.032889101958498534,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.9544336312499999,
        0.034328868750000005,
        0.01081636875,
        0.0004211312500000001
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.5,
      "theta": 0.25,
      "fpr_both": 0.01,
      "sensitivity_1": 0.2575,
      "sensitivity_2": 0.071875,
      "queries": 500000,
      "detector_evaluations": 1000000,
      "replicates": 10000,
      "coverage": 0.9989,
      "coverage_mc95": [
        0.9980326505194581,
        0.9994507601153076
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.03781327997230442,
      "median_interval_width": 0.037809417875334955,
      "p95_interval_width": 0.03864677754791607,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.8346164062499999,
        0.12444609375,
        0.031633593749999994,
        0.009303906249999999
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.5,
      "theta": 0.5,
      "fpr_both": 0.01,
      "sensitivity_1": 0.505,
      "sensitivity_2": 0.2575,
      "queries": 200000,
      "detector_evaluations": 400000,
      "replicates": 10000,
      "coverage": 0.9995,
      "coverage_mc95": [
        0.9988335557909334,
        0.9998376320658011
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.03154279614519007,
      "median_interval_width": 0.03154014400503616,
      "p95_interval_width": 0.03201629423686281,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.6738187499999999,
        0.19243125,
        0.06868125,
        0.06506875
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.5,
      "theta": 0.75,
      "fpr_both": 0.01,
      "sensitivity_1": 0.7525,
      "sensitivity_2": 0.566875,
      "queries": 100000,
      "detector_evaluations": 200000,
      "replicates": 10000,
      "coverage": 1.0,
      "coverage_mc95": [
        0.9996311800853812,
        1.0
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.03012710264088464,
      "median_interval_width": 0.030128791712185382,
      "p95_interval_width": 0.030456948977925533,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.5436492187499999,
        0.16791328125,
        0.07510078125000001,
        0.21333671875
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.9,
      "theta": 0.05,
      "fpr_both": 0.01,
      "sensitivity_1": 0.059500000000000004,
      "sensitivity_2": 0.012475,
      "queries": 50000000,
      "detector_evaluations": 100000000,
      "replicates": 10000,
      "coverage": 0.9939,
      "coverage_mc95": [
        0.9921711011041445,
        0.9953308648444829
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.0339845924265327,
      "median_interval_width": 0.033977587810487764,
      "p95_interval_width": 0.034681303126861504,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.9339005362499999,
        0.05387196375,
        0.011549463749999999,
        0.0006780362500000001
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.9,
      "theta": 0.25,
      "fpr_both": 0.01,
      "sensitivity_1": 0.2575,
      "sensitivity_2": 0.071875,
      "queries": 1000000,
      "detector_evaluations": 2000000,
      "replicates": 10000,
      "coverage": 0.9987,
      "coverage_mc95": [
        0.9977779863787409,
        0.9993076289114248
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.03328619794974137,
      "median_interval_width": 0.03328656327039953,
      "p95_interval_width": 0.03365954813809648,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.7182295312499999,
        0.21608296875,
        0.04902046874999999,
        0.01666703125
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.9,
      "theta": 0.5,
      "fpr_both": 0.01,
      "sensitivity_1": 0.505,
      "sensitivity_2": 0.2575,
      "queries": 200000,
      "detector_evaluations": 400000,
      "replicates": 10000,
      "coverage": 0.9989,
      "coverage_mc95": [
        0.9980326505194581,
        0.9994507601153076
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.03733000782373546,
      "median_interval_width": 0.037331254294961314,
      "p95_interval_width": 0.037739500647225574,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.42879375,
        0.33845624999999996,
        0.11570625000000001,
        0.11704375
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    },
    {
      "rho": 0.9,
      "theta": 0.75,
      "fpr_both": 0.01,
      "sensitivity_1": 0.7525,
      "sensitivity_2": 0.566875,
      "queries": 100000,
      "detector_evaluations": 200000,
      "replicates": 10000,
      "coverage": 0.9994,
      "coverage_mc95": [
        0.9986945135169888,
        0.9997797797613424
      ],
      "precision_probability": 1.0,
      "precision_mc95": [
        0.9996311800853812,
        1.0
      ],
      "mean_interval_width": 0.030607566992858545,
      "median_interval_width": 0.030605577062814193,
      "p95_interval_width": 0.03084920551747038,
      "empty_set_fallbacks": 0,
      "joint_probabilities_00_10_01_11": [
        0.19448859375,
        0.29432390625,
        0.12726140625000001,
        0.38392609375000003
      ],
      "selection_passed": true,
      "precision_criterion_met": true,
      "query_count_interpretation": "Smallest candidate passing the frozen selection rule, independently confirmed once; not an exact minimal sample size"
    }
  ]
}
```

## Frozen protocol

```json
{
  "experiment": "T12-C",
  "not_before_utc": "2026-11-18T19:36:00+00:00",
  "seed": 2026111803,
  "fpr": 0.01,
  "rho_grid": [
    0.1,
    0.5,
    0.9
  ],
  "theta_grid": [
    0.05,
    0.25,
    0.5,
    0.75
  ],
  "query_grid": [
    1000,
    2000,
    5000,
    10000,
    20000,
    50000,
    100000,
    200000,
    500000,
    1000000,
    2000000,
    5000000,
    10000000,
    20000000,
    50000000,
    100000000
  ],
  "selection_replicates": 2000,
  "confirmation_replicates": 10000,
  "selection_precision_rate": 0.975,
  "confidence_alpha": 0.05,
  "target_width": 0.04,
  "target_precision_probability": 0.95,
  "primary_table_rho": 0.5,
  "analysis": "Conditional oracle-calibration simulation. Channel sensitivities are f+(1-f)*theta and f+(1-f)*theta^2. Query outcomes share one latent marking indicator. Conditional detector flags are independent given mark, so marginal flags are correlated. Select the smallest frozen query-grid n with at least 97.5 percent narrow intervals in 2000 selection replicates, then validate exactly once on 10000 independent confirmation replicates. Criterion is the lower endpoint of a two-sided exact 95 percent Monte Carlo interval for P(CI width<=0.04) at least 0.95. Report coverage and precision MC intervals. If no n passes selection, confirm the maximum n and label not attained. No repeated confirmation search. This is not empirical calibration on real 50-token text.",
  "frozen_utc": "2026-11-18T19:27:18.635847+00:00"
}
```
