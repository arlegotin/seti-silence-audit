# Third-party attribution and boundaries

[LICENSING.md](LICENSING.md) defines the original project licenses. External
articles, archive material, cited work, license documents and dependencies
retain their upstream terms. No endorsement by the survey authors, UCLA,
Green Bank Observatory or Dryad is implied.

## UCLA 2020–2023 survey

Credit Jean-Luc Margot, Megan G. Li, Pavlo Pinchuk, Nathan Myhrvold,
Larry Lesyna and the other authors of *A Search for Technosignatures Around
11,680 Stars with the Green Bank Telescope at 1.15–1.73 GHz*, The Astronomical
Journal 166, 206 (2023).
[Paper](https://arxiv.org/html/2308.02712v4),
[DOI](https://doi.org/10.3847/1538-3881/acfda4).

The retained [HTML](inputs/ucla_2308.02712v4.html), arXiv version 4, declares
**CC BY-NC-SA 4.0**. It is retained unchanged, with its license and author
notices. The project's AGPL/CC BY grants do not replace its noncommercial and
share-alike terms. See the
[upstream license](https://creativecommons.org/licenses/by-nc-sa/4.0/).

[data/source_rows.csv](data/source_rows.csv), [data/targets.csv](data/targets.csv),
the site geometry and the embedded target transcription in
[the blueprint](docs/blueprint.md) derive from Appendix A, Tables 5–6. Processing
parses coordinates and distances, converts them to Cartesian light-year
positions, and links two visits to TOI 1730.01 as one physical site. Credit the
survey authors for the source measurements and tables. To the extent an adapted
table carries upstream copyright, it retains CC BY-NC-SA 4.0; numerical facts
themselves are not exclusively licensed by this project. The transcript is not
an independently measured catalog.

## Dryad dataset and metadata

Credit Jean-Luc Margot, Megan G. Li, Pavlo Pinchuk, Nathan Myhrvold,
Larry Lesyna, Liam Rindt and Ryan S. Lynch for *Data from: A Search for
Technosignatures Around 11,680 Stars with the Green Bank Telescope at
1.15–1.73 GHz* (2025), Dryad version 370211.
[Dataset and license declaration](https://doi.org/10.5061/dryad.wm37pvn0b).

The dataset declares **CC0 1.0**. The repository retains public API metadata,
the landing-page snapshot and access/integrity records under [inputs](inputs).
Dryad's website presentation and third-party notices are retained as supplied;
the dataset's CC0 declaration is not a new license grant over the entire website.
The four candidate CSV files and the archive README were not obtained. Their
listed hashes and sizes are expectations from metadata, not evidence that those
files were processed. Raw telescope recordings are not bundled.

## Original supporting research note

The supplied mathematical note is
[Silence, expansion speed, and a Dirichlet law for early contact](docs/silence_contact_theorem.pdf),
dated 1 November 2026, SHA-256
`2a6c071a3edfc6ff3dc5db07ac4c94448537f907e9e22051f9397b49374839fe`.
The note is by **Artem Legotin**, who confirmed authorship and authorized its
publication under **CC BY 4.0** for this release. It is original project material,
covered by [LICENSING.md](LICENSING.md). The historical PDF contains no named
author or license and is retained unchanged for provenance. The frozen design
records describe the unattributed handoff as it existed then. The audit
independently repaired the incomplete warning display and did not obtain the
note's claimed original computation scripts.

## Scientific dependencies and assistance

NumPy, SciPy, Matplotlib, pytest, mpmath, setuptools and their dependencies retain
the licenses and notices in their separately installed distributions. The source
and wheel do not bundle dependency binaries, virtual environments or package
caches. [requirements.lock.txt](requirements.lock.txt) records the scientific
versions; [the environment record](results/environment.json) describes the
measured installation.

Development and reporting used AI assistance under Artem Legotin's direction.
README editing used [write-like-me](https://github.com/arlegotin/write-like-me).
The writing skill and its reference material are not bundled.
