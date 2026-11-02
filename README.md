# SETI silence audit

**Does hearing no alien radio signals tell us anything about whether a civilization could reach Earth?**

This repository tests that connection using the published target catalog from
the UCLA 2020–2023 Green Bank Telescope survey and simulations of civilizations
expanding between stars. It asks how much the survey's lack of detections changes
the largest arrival probability among a declared set of hypothetical scenarios.
The arrival window is the 100 years after the survey.

[Results](report/REPORT.md) · [Reproduce](REPRODUCE.md) · [Design](docs/blueprint.md) · [Citation](CITATION.cff)

## What happened

**For strong, persistent radio broadcasters, the upper modeled arrival risk
falls from roughly 11% to 4% after accounting for the survey's silence.**
Silence filters out some of the scenarios with higher arrival risk because
those scenarios would also have been more likely to produce a detectable signal.

Those percentages describe this finite model family, conditioned on Earth not
already having been reached. **They aren't estimates of Earth's actual chance
of alien visitors.** The model includes only the survey's 61 distinct primary
target sites; the original telescope beams covered about 11,680 stars.

The other comparisons matter:

- **Uncertain detector performance:** for persistent broadcasters, the modeled
  upper risk stays below 8% across the full assumed detection-efficiency range
  of 44–94%. That range is an assumption, not a measured calibration interval.
- **Uncommon, short-lived or intermittent broadcasting:** under the nominal
  detector, the reduction fails the project's declared threshold for a
  meaningful effect. Allowing an invisible counterpart of every scenario
  prevents a reduction across the full family.
- **Interactions between civilizations:** a simpler model treating sites
  independently also gives an upper risk of about 4% in the main comparison.
  The extra interaction mechanism doesn't establish a distinct advantage here.

The useful result is knowing which assumptions make the radio observation
informative about arrival, and where that inference loses its force. Generic
inference from SETI nondetections already has
[prior art](docs/blueprint.md#11-what-is-new-enough-to-investigate).

## What came from real observations

The real inputs are the published star positions, distances, observing-date
ranges and reported nondetection. All **62 catalog rows** were checked against
the [survey paper](https://arxiv.org/html/2308.02712v4); one target appears twice,
so the model uses **61 physical sites** and preserves the repeated visit.

Most computation is simulation. The audit varies civilization birth rates,
expansion speeds, broadcasting behavior and detection assumptions, then compares
arrival risk before and after conditioning on the radio result.

**Raw telescope recordings were not reanalysed.** The archived candidate CSVs
were not obtained, complete scan timestamps remain unavailable, and published
signal-recovery statistics don't establish the probability of passing every
final detection filter. The saved run therefore uses bounded observing times
and assumed detector response. A telescope-calibrated forecast remains unsupported.

## Rebuild the report

From a clone, use Python 3.12 and the pinned dependencies:

```sh
git clone https://github.com/arlegotin/seti-silence-audit.git
cd seti-silence-audit
python3.12 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install -e . --no-deps
MPLCONFIGDIR=/tmp/seti-silence-mpl .venv/bin/python -m seti_audit report --protocol results/protocol.lock.json --from-results --out /tmp/seti-silence-report
```

Open `/tmp/seti-silence-report/REPORT.md`. After installation, reconstruction
needs no network, new simulations or raw checkpoint store. It reads the committed
compressed aggregate evidence and regenerates the tables and figures. Generated
evidence paths and bookkeeping files in the checkout are updated too.

The completed audit passes **250 offline tests**:

```sh
.venv/bin/python -m pytest -q
```

The recorded environment is Python 3.12 on ARM64 macOS. See
[REPRODUCE.md](REPRODUCE.md) for smoke checks, new experiments, historical code
pins and the boundary between rebuilding a report and rerunning its simulations.
The declared audit is complete; the [review record](docs/final_review.md) describes
the fresh-context AI code review, its three findings and the verified fixes.

By **Artem Legotin**. Original software is **AGPL-3.0-only**; original writing and
result compilations are **CC BY 4.0**, with [separate scopes](LICENSING.md) and
[upstream attribution](THIRD_PARTY_NOTICES.md). Cite [CITATION.cff](CITATION.cff)
and record the commit used. Development and reporting used AI assistance under
Artem Legotin's direction. README editing used
[write-like-me](https://github.com/arlegotin/write-like-me).
