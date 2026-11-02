# Public release preparation

Release prepared on 2 November 2026 for
[arlegotin/seti-silence-audit](https://github.com/arlegotin/seti-silence-audit).
The scope is the completed conditional audit, with the F1 bounded-time and F2
assumed-detector limitations preserved. No new scientific experiment was run
to change the reported research findings.

## Presentation and licensing

The README opens with the research question and the conditional 11% to 4%
result. It separates real catalog/date/nondetection inputs from simulations,
states the 61-site population and distinguishes model results from a forecast
for Earth. The former command reference is preserved in
[REPRODUCE.md](../REPRODUCE.md).

The licensing and citation format follow the author's recent public research
repositories, including RCU Bench and Repair-aware library admission:
AGPL-3.0-only software and CC BY 4.0 original writing/result compilations.
[LICENSING.md](../LICENSING.md) defines the scopes;
[THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) preserves source attribution
and exceptions. The survey HTML retains CC BY-NC-SA 4.0 and the archive dataset
declares CC0. The original supporting note is by Artem Legotin, who confirmed
ownership and authorized CC BY 4.0 publication. Its bytes and historical labels
are unchanged.

[CITATION.cff](../CITATION.cff) identifies the software, its author, version,
repository, scoped licenses, all 80 survey authors and the supporting note.
It passed the CFF 1.2.0 schema validator. It claims no project DOI or external
journal publication. README editing used the requested
[write-like-me](https://github.com/arlegotin/write-like-me) skill; the private
skill and its references are not bundled.

## Validation

The [machine-readable receipts](public_release_verification.json) retain the
commands, outputs, timings and hashes, with local path prefixes normalized.

- The fresh source copy passed all **250 tests** in 40.90 seconds.
- Report generation from committed evidence succeeded without raw checkpoint
  stores. All ten table/conclusion/envelope artifacts matched the saved results.
- A newly built wheel contained the declared author, SPDX license expression,
  full license texts/notices and byte-identical copies of all 19 source modules.
  Its installed smoke path and complete saved-evidence report passed; scientific
  output hashes matched again.
- Relative links in the release documentation were checked. Source code,
  tests, the blueprint, specification, plan, theorem PDF, protocol locks and
  numerical evidence retain their prior hashes. Package metadata and release
  documentation do not rewrite historical readiness records.

## History and release boundary

A local pattern scan covered all 23 existing commits, 260 unique reachable
blobs and gzip/zip contents: 206,303,466 inspected bytes, including decompressed
contents. It found no unresolved credential exposure and no tracked sensitive
credential filenames. One generic API-key match is the public, domain-scoped
AWS WAF CAPTCHA client configuration in the unchanged anonymous Dryad page.
That field belongs in public client JavaScript; see the
[AWS documentation](https://docs.aws.amazon.com/waf/latest/developerguide/waf-js-captcha-api.html).
Anonymous public-page anti-CSRF form fields are retained with that source
snapshot; no corresponding session cookies are bundled. This review is scoped
to the documented patterns and inspected source context, not a guarantee that
every possible secret format can be detected.

Virtual environments, package caches, raw checkpoint stores and ignored
scratch material are outside the public Git contents. Original Git history is
preserved so the pinned numerical checkout remains available. Publication uses
the requested current `main` branch, an ordinary push to the originally empty
private remote, then the explicitly authorized change to public visibility.
No scientific stopping rule or execution cap was added.
