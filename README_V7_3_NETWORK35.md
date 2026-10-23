# V7.3: Recovery paths for the 35 network-error domestic sources

**Scope:** Based on the user-supplied 2026-10-18 GitHub Actions logs. This patch layers on top of V7.1 and V7.2. No frontend files, existing source list, international adapters, international crawling rules, scheduled workflow or historical data files are changed.

## What actually changes

- `diagnostics/network35_official_recovery_routes.json`: maps all 35 previous connection-error source IDs to explicit provincial government publication directories and other official departmental indices. One source, Shanxi Energy Bureau, was already fixed in V7.1 and is deliberately protected; recovery is active for the remaining 34. This covers 13 provinces/regions.
- `policy_domestic_network35.py`: executable fallback collector. It is called after an original-site transport failure (or an empty/unproven document directory) for one of these 34 IDs. Up to two distinct government-publisher directories are tried. The collector reads real dated list rows, up to two pages per directory and up to three full details; it retains dated leads when the detail is missing. A shared, thread-safe cache prevents duplicate queries to the same provincial directory during a run.
- `policy_scrape.py`: integrates fallback, records its attempts/observed policy count, preserves original failure/coverage evidence and does not advance the original source's verified date cursor based on another authority's index. The familiar frontend status code `partial_coverage` is used when cross-publisher documents are found. This does not mean the failed original source is working.
- `diagnostics/network35_source_actions.csv`: all 35 affected sources, original URLs, fallback URLs, and evidence levels. Some backup URLs are supported by public official directory search results; others are sourced from previously configured official candidate channels and are explicitly *not* live-verified.
- `tests/test_policy_domestic_network35.py`: regression tests for source membership and protection, provenance, publication date, paging, navigation filtering, site challenges, errors, and non-advancement of coverage cursors.

## What the runtime report will tell you

After a successful `--scope provincial` crawl, `diagnostics/network35_runtime_report.csv` and the companion JSON record per source:

- Whether it ran in this job and its current original-site status.
- Whether it attempted official backup; for each backup, what happened (read, no dated topic rows, blocked/error, details pending).
- Number of dated policy records/confirmed leads obtained via the separate issuer.
- Whether the original issuing department's chronological list has been fully verified. Fallback publications never certify this by themselves.

These are uploaded by the existing GitHub Actions `wind-policy-backend-diagnostics` artifact. The backend acceptance CSV in `site/data` also includes recovery diagnostics. No frontend HTML, JavaScript or CSS changes were made.

## Limitations and acceptance

Connection failures at the transport layer cannot be repaired with CSS selectors. This patch adds separate official paths that may be accessible when the old source is inaccessible. It does **not** claim that all 35 original URLs are reachable, that every backup is reachable from GitHub, or that a different issuer provides complete coverage of the original agency.

The executing runtime in this handoff cannot successfully resolve/reach many external government domains. Live success must be audited from the next actual GitHub Actions run and can still require site-specific follow-up.

Source provenance and the original invalid cursor are retained. Government sources should not be treated as interchangeable: a provincial government file archive may offer genuine wind policy documents without replacing the energy bureau's own notices. A source may yield a verified dated policy yet remain `partial_coverage`.

## Install

1. Back up your repository and `site/data`. Make sure V7.1 and V7.2 changes are already present.
2. Unpack `wind-policy-v7-3-network35-PATCH.zip` over the repository root, preserving `.git` and `.github`.
3. Commit/push using GitHub Desktop.
4. Actions -> existing collection/deployment workflow -> Run workflow -> `provincial`.
5. Wait until the complete workflow finishes. Download `wind-policy-backend-diagnostics` and open `network35_runtime_report.csv`; also review `site/data/policy_site_acceptance.csv` and actual policy URLs.
6. If the primary and both backup government hosts still fail, the runtime environment remains a blocker. A successful offline unit test is **not** a live HTTP acceptance result.

Do not upload a complete historical ZIP over newer deployed data when the incremental patch suffices.
