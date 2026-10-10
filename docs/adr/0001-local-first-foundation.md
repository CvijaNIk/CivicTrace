# ADR 0001: local-first modular foundation
Status: accepted for foundation, 2026-10-10.

Choose a Python package and static frontend target, with no running server in the foundation.
A dependency-free synthetic path makes first contributions and offline use practical. Heavy
libraries are optional until integration tests establish their role. Keep the existing Apache-2.0
license instead of replacing it: explicit patent provisions suit community extensions; MIT would
be simpler but would not provide the same explicit patent grant.

Alternatives: full-stack hosted SaaS would add operating costs, authentication and private-data
handling; distributed processing would complicate unmeasured workloads. Both are deferred.
Consequences: no real source, web UI or big-data claim yet; CI installs development tools, and
future browser/private-data paths require explicit security and size-limit validation.
