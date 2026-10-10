# Security model
| Risk | Required mitigation before implementation |
| --- | --- |
| Malicious public files | Bound input/decompressed bytes and row counts, validate schemas, quarantine errors, reject unsafe archive paths |
| Network sources / SSRF | Reviewed publisher allowlist, HTTPS, redirect policy, timeouts/backoff, size limits; no arbitrary URL fetch |
| HTML and CSV exports | Escape source strings; allow safe URL schemes; neutralize spreadsheet formula injection |
| SQL / extensions | Parameterized read-only queries; no network/file extensions or arbitrary contributor execution |
| Private data exposure | Local-only defaults, no telemetry or uploads, no public build inclusion, local export warning/preview |
| Malicious PRs | Least-privilege CI, pinned action commits, code review, no fork secrets, no pull_request_target execution |
| Supply chain | Bounded dependencies initially; lock/hashes and advisory checks before release, reviewed Dependabot PRs |
| False matches / stale lists | Exact scheme identifiers, explicit candidate status, source dates, human verification and correction |
| Source authenticity | Preserve bytes/hash/license evidence; explain hash limits and transformations |

Current CLI is offline and does not render HTML, evaluate SQL or unpack archives. It rejects some
malformed synthetic records and refuses to overwrite output, but is not a hardened untrusted-file
parser. Input size caps and richer validation must precede private-file or public-source release.
No confidential whistleblower hosting, active scanning or privileged extension runtime is planned
for the first release. Browser local-only claims require network-observation tests, including worker
and dependency behavior, before being presented as verified capabilities.
