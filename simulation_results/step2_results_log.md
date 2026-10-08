# Step 2 results log: does the order book show a critical load?

Working notes for writing the README. Numbers are copied from actual runs; nothing here is estimated.
Branch: `lob-simulator`. Last updated 2026-10-07. Status: **FINAL for Step 2: negative at gamma = 3 and gamma = 10 under the README success rule (Results 1 and 3); event-level check shows the coupling is real but weak (Result 2); the one planned redesign (refill suppression) failed its gate, so no further attempts.**

## Setup (common to the runs below)

| Item | Value |
|---|---|
| Simulator | `phantom/lob_sim.py`; lambda = 1.0, theta = 0.02, mean offset 2, sizes uniform 1..5 |
| Coupling | cancelled volume at a tick -> decaying stress (memory 50 events, relative to depth); orders on the tick behind get cancel rate x (1 + gamma * stress) |
| Load | rho = mu / lambda, swept through mu |
| Signal | change in depth per 50-event window at levels 0-4, per side (windows with an empty side at either end are NaN) |
| Measure | peak lagged correlation over lags 0-9 windows, adjacent levels (touch leads), no wrap-around, mean over 4 pairs x 2 sides |
| Run | 40,000 events, first 5,000 dropped (700 windows), 20 runs per point |
| Success rule (README) | rise >= 0.40 across a narrow band of loads, and the gamma = 0 control never above 0.20 |

Instrument checks done before running: planted outward cascade gives 0.963 (reversed direction 0.026, pure noise 0.046);
10% scattered NaN windows still give 0.958; the ring (traffic) path reproduces the saved Phase 1 values bit for bit.

## Result 1: load sweep, gamma in {0, 3} (`data/lob_sweep.npz`, seed 0, 11.5 minutes)

| load | gamma=0 peak (std) | gamma=0 dropped | gamma=0 top-tick depth | gamma=3 peak (std) | gamma=3 dropped | gamma=3 top-tick depth |
|---|---|---|---|---|---|---|
| 0.05 | 0.070 (0.010) | 0.0% | 124.4 | 0.096 (0.008) | 0.0% | 75.0 |
| 0.10 | 0.066 (0.006) | 0.0% | 116.9 | 0.094 (0.012) | 0.3% | 61.8 |
| 0.15 | 0.073 (0.009) | 0.0% | 109.0 | 0.105 (0.020) | 0.6% | 51.9 |
| 0.20 | 0.080 (0.010) | 0.0% | 101.7 | 0.100 (0.015) | 1.2% | 46.8 |
| 0.25 | 0.090 (0.016) | 0.0% | 93.7 | 0.100 (0.018) | 1.9% | 42.3 |
| 0.30 | 0.095 (0.014) | 0.0% | 85.5 | 0.104 (0.010) | 3.0% | 39.3 |
| 0.35 | 0.091 (0.011) | 0.1% | 77.7 | 0.113 (0.017) | 4.1% | 36.2 |
| 0.40 | 0.094 (0.012) | 0.1% | 70.4 | 0.120 (0.015) | 6.1% | 33.5 |
| 0.45 | 0.082 (0.012) | 0.7% | 62.1 | 0.124 (0.014) | 8.2% | 30.9 |
| 0.50 | 0.082 (0.007) | 1.1% | 54.6 | 0.118 (0.017) | 10.8% | 28.9 |
| 0.55 | 0.088 (0.012) | 2.2% | 49.5 | 0.127 (0.018) | 13.7% | 26.7 |
| 0.60 | 0.084 (0.013) | 4.0% | 43.0 | 0.129 (0.014) | 16.9% | 24.5 |
| 0.65 | 0.089 (0.014) | 6.0% | 38.1 | 0.126 (0.011) | 20.2% | 23.0 |
| 0.70 | 0.090 (0.012) | 8.9% | 33.3 | 0.129 (0.017) | 24.1% | 21.6 |
| 0.75 | 0.094 (0.011) | 12.5% | 30.0 | 0.135 (0.011) | 27.7% | 20.2 |
| 0.80 | 0.104 (0.016) | 17.5% | 26.2 | 0.140 (0.020) | 31.8% | 18.8 |

Summary against the README success rule:

| | low plateau (rho <= 0.20) | high plateau (rho >= 0.60) | rise |
|---|---|---|---|
| gamma = 0 | 0.072 | 0.092 | +0.020 |
| gamma = 3 | 0.099 | 0.132 | +0.033 |

- Control condition holds: gamma = 0 never above 0.104 (limit 0.20).
- **Transition condition fails**: gamma = 3 rises +0.033, about 8% of the required +0.40. The curve is a slow drift. The largest step between adjacent loads is +0.011 (traffic: 0.3 to 0.4 per 0.01 density step). No threshold.
- gamma = 3 is 0.008 to 0.045 above the control at every load; one mean has a standard error of about 0.003, so the gap is real but small.
- Confound: the coupled book holds much less volume (top-tick depth 75 vs 124 at load 0.05, 18.8 vs 26.2 at load 0.80), so even the small gap may partly be thinness.
- Dropped windows grow with load, reaching 17.5% (gamma = 0) and 31.8% (gamma = 3) at load 0.80.

## Result 2: event-level check of the coupling (`scripts/check_coupling.py`, 5 runs per point, seed 0)

Mean number of cancellations within 50 events after a cancellation, at the tick behind it / ahead of it / two behind it
(+- standard error in the script output; rounded here).

| load | gamma | behind | ahead | two behind |
|---|---|---|---|---|
| 0.10 | 0 | 1.537 | 1.535 | 1.031 |
| 0.10 | 3 | 1.652 | 1.431 | 1.033 |
| 0.10 | 10 | 1.519 | 1.352 | 0.967 |
| 0.40 | 0 | 0.959 | 0.922 | 0.715 |
| 0.40 | 3 | 1.073 | 0.812 | 0.726 |
| 0.40 | 10 | 1.105 | 0.805 | 0.747 |
| 0.70 | 0 | 0.442 | 0.418 | 0.363 |
| 0.70 | 3 | 0.671 | 0.442 | 0.444 |
| 0.70 | 10 | 0.803 | 0.524 | 0.522 |

Extra cancellations behind a cancellation caused by the coupling (behind minus the gamma = 0 value):

| load | gamma = 3 | gamma = 10 |
|---|---|---|
| 0.10 | +0.115 | -0.018 |
| 0.40 | +0.114 | +0.146 |
| 0.70 | +0.229 | +0.361 |

## Result 3: load sweep, gamma = 10 (`data/lob_sweep_gamma10.npz`, seed 1, independent of Result 1's streams)

Same settings as Result 1 (16 loads, 20 runs, 40,000 events). gamma = 0 and gamma = 3 columns are copied from Result 1.

| load | gamma=0 | gamma=3 | gamma=10 peak (std) | gamma=10 dropped | gamma=10 top-tick depth |
|---|---|---|---|---|---|
| 0.05 | 0.070 | 0.096 | 0.109 (0.012) | 0.6% | 57.2 |
| 0.10 | 0.066 | 0.094 | 0.123 (0.017) | 2.3% | 50.4 |
| 0.15 | 0.073 | 0.105 | 0.132 (0.015) | 5.4% | 39.0 |
| 0.20 | 0.080 | 0.100 | 0.139 (0.016) | 8.4% | 33.0 |
| 0.25 | 0.090 | 0.100 | 0.155 (0.021) | 11.1% | 29.2 |
| 0.30 | 0.095 | 0.104 | 0.153 (0.014) | 14.4% | 26.5 |
| 0.35 | 0.091 | 0.113 | 0.165 (0.023) | 17.2% | 24.5 |
| 0.40 | 0.094 | 0.120 | 0.157 (0.021) | 19.8% | 23.1 |
| 0.45 | 0.082 | 0.124 | 0.151 (0.023) | 23.2% | 21.3 |
| 0.50 | 0.082 | 0.118 | 0.149 (0.020) | 26.6% | 20.1 |
| 0.55 | 0.088 | 0.127 | 0.152 (0.018) | 29.9% | 18.8 |
| 0.60 | 0.084 | 0.129 | 0.154 (0.018) | 33.3% | 17.8 |
| 0.65 | 0.089 | 0.126 | 0.153 (0.021) | 36.3% | 16.8 |
| 0.70 | 0.090 | 0.129 | 0.158 (0.023) | 40.0% | 15.9 |
| 0.75 | 0.094 | 0.135 | 0.153 (0.015) | 43.6% | 15.2 |
| 0.80 | 0.104 | 0.140 | 0.151 (0.018) | 45.5% | 14.5 |

| | low plateau (rho <= 0.20) | high plateau (rho >= 0.60) | rise | max over loads |
|---|---|---|---|---|
| gamma = 0 | 0.072 | 0.092 | +0.020 | 0.104 |
| gamma = 3 | 0.099 | 0.132 | +0.033 | 0.140 |
| gamma = 10 | 0.126 | 0.154 | +0.028 | 0.165 |

- **Transition condition fails again**: rise +0.028, 7% of the required +0.40. Largest step between adjacent loads +0.016 (loads 0.20 to 0.25).
- The curve climbs from 0.109 to about 0.165 by load 0.35 and then flattens (0.15 to 0.16): a plateau, not a threshold.
- gamma = 10 is 0.040 to 0.073 above the control, and 0.011 to 0.055 above gamma = 3. Raising gamma from 3 to 10 buys little, consistent with the event-level saturation in Result 2.
- Depth is still about half of the control (ratio 0.46 at load 0.05, 0.55 at load 0.80), so the confound persists.
- **The measured sample shrinks sharply at high load**: dropped windows pass 20% at load 0.40 and reach 45.5% at load 0.80. The upper half of this curve rests on a heavily filtered sample, so it should be read with that caveat.

## What the evidence supports (and what it does not)

- Supported: the coupling works as designed at the event level. Cancellations are followed by more cancellations on the tick
  behind it than the control, the effect is larger at high load (thin book), and it is directional (the tick ahead does not gain).
- Supported: the effect is far too weak to cascade. A cascade needs roughly one extra cancellation per cancellation; the
  coupling adds 0.1 to 0.36 per cancellation within 50 events, and gamma = 10 adds little over gamma = 3 (it saturates).
- Plausible but NOT tested: saturation happens because a tick holds only a few orders; once they are cancelled there is nothing
  left to cancel until limit orders refill it. The raw counts also compare books of different depth, which pushes the measured
  excess downward, so it is somewhat understated.
- Not shown: that no coupling of this general kind could produce a transition. Only this rule, at gamma = 3 (sweep) and
  gamma = 3, 10 (event level), has been tried.

## Pending

- Decision taken (2026-10-07): ONE redesign attempt, refill suppression (sigma, `refill_suppression` in `LOBParams`, hook
  `adjust_for_stress` in `phantom/lob_sim.py`). sigma = 0 reproduces the earlier generator bit for bit.

## Redesign attempt: rules fixed before running

- **Gate (cheap, ~1 minute):** `scripts/check_coupling.py` at load 0.7. The extra cancellations behind a cancellation
  (value minus the gamma = 0 value of 0.442) must reach **at least 0.5**, for at least one of the two settings below.
  For reference, the earlier coupling gave +0.229 (gamma = 3) and +0.361 (gamma = 10).
- **Settings tried, fixed in advance:** (gamma = 3, sigma = 1) and (gamma = 3, sigma = 5). No other values.
- **If the gate passes:** run the full load sweep once with the passing setting (same 16 loads, 20 runs, 40,000 events) and
  judge it with the unchanged README success rule.
- **If the gate fails for both settings:** stop. The null result is the finding, and the write-up says the coupling was
  also tried with refill suppression.
- **No further redesigns after this one.**

## Redesign attempt: gate result (FAILED, so no sweep was run)

Design as implemented (`adjust_for_stress`): a new limit order is SKIPPED with probability min(1, sigma * stress), with the
stress read at the tick AHEAD of the post (same tick relation as the cancel rule). Skipped volume leaves the system.
Checked on planted books first: skip rate matched sigma * stress (0.748 vs 0.75; 0.367 vs 0.375), ignored the target tick's own
stress, worked on both sides, and sigma = 0 stayed bit-identical to the earlier generator.

Event-level gate (`scripts/check_coupling.py`, gamma = 3, 5 runs per point, seed 0): cancellations within 50 events after a
cancellation, at the tick behind it.

| load | no suppression (gamma = 3) | sigma = 1 | sigma = 5 | gamma = 0 reference |
|---|---|---|---|---|
| 0.10 | 1.652 | 1.295 | 0.207 | 1.537 |
| 0.40 | 1.073 | 0.757 | 0.471 | 0.959 |
| 0.70 | 0.671 | 0.442 | 0.325 | 0.442 |

- Gate: extra cancellations behind at load 0.7 (value minus the gamma = 0 value of 0.442) must be at least 0.5, i.e. at least 0.942.
- **Measured: sigma = 1 gives 0.442 (extra 0.000), sigma = 5 gives 0.325 (extra -0.117). Both fail by a wide margin.**
- Refill suppression REDUCED follow-up cancellations (from +0.229 without it to about 0 or negative). Triggering cancellations per run also fell
  (7,615 without suppression to 4,438 at sigma = 1 and 4,060 at sigma = 5, load 0.7).
- Skipped fraction of limit orders (20,000-event runs, gamma = 3): sigma = 1: 34.8% at load 0.1, 26.4% at 0.7; sigma = 5: 45.3% at 0.1, 26.1% at 0.7.
  So the effective lambda is 55% to 74% of nominal, and the nominal load axis understates the real one.
- Likely mechanism (interpretation, not separately tested): with this design the same tick receives a higher cancel hazard
  AND fewer new posts. Pressure goes up, but the supply of orders to cancel there goes down, and supply wins. At sigma = 5, load 0.1,
  the tick behind has 0.207 follow-ups while the tick two behind has 0.827: the tick next to the stress is starved, the next one is not.
- Caveat: raw counts compare books of different depth, and the suppressed book is thinner, which lowers counts mechanically. A count
  normalised by resting orders would separate the two effects; it was not part of this attempt.
- Per the rule fixed in advance: **stop**. The null result stands and the write-up should say refill suppression was also tried.

## Figure

`graphs/lob_sweep_results.png`, made by `python -m scripts.make_lob_plots` from `data/lob_sweep.npz` (gamma = 0, 3) and
`data/lob_sweep_gamma10.npz` (gamma = 10). Left: mean peak lagged correlation against load for the three settings, the control
limit (0.20), and a grey band at the level a transition would need (low-load plateau + 0.40, 0.50 to 0.53). Single panel by choice;
the share of windows dropped (0.6% to 45.5%) is in the tables above and belongs in the README's limitations text instead of the figure.
Light surface; series colours are the validated categorical slots 1 to 3, and aqua is under 3:1
contrast so identity is also carried by direct labels, a legend and marker shapes.

## Points the README could make (in your own words)

- The order book did not show a threshold under this coupling; the control stayed flat, so the measurement itself is not creating structure.
- The planted-signal tests show the measure can see a cascade (0.96) and respects direction (0.03 reversed), so the null is about the coupling, not the instrument.
- The event-level check shows the coupling is real but weak, which explains the result.
- The unmatched depth is a limitation that applies to the small gamma = 3 gap.
