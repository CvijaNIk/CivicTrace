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
parser. The bounded JSON intake described below is one prerequisite; broader validation and
independent review still precede private-file or public-source release.
No confidential whistleblower hosting, active scanning or privileged extension runtime is planned
for the first release. Browser local-only claims require network-observation tests, including worker
and dependency behavior, before being presented as verified capabilities.

## Bounded JSON intake — 20 October 2026

The CLI now limits input to 1 MiB, JSON depth to 32, records to 10000, number
tokens to 128 characters and required identity/reference strings to 4096
characters. It checks the opened descriptor is a regular file, reads at most
the byte budget plus one, and uses nonblocking opening to reject FIFOs on
POSIX. UTF-8 (optional BOM) is required. Duplicate keys, nonfinite numbers and
non-object records are rejected with controlled CLI errors before output.
Original bytes remain the evidence hash source. No data is fetched or uploaded.

These limits bound this synthetic JSON workflow; they are not an OS sandbox,
source-authentication guarantee, malware scan, streaming parser, archive/media
defense or production-input certification. Direct library callers already hold
their objects in memory and remain responsible for allocation before calling.
See `INPUT_SECURITY_2026_10_20.md` for verification, compatibility and rollback.
