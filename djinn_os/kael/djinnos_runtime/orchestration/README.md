# Kael orchestration

Kael is operational packaging only.

Allowed:
- containerization
- port mapping
- health checks
- logs
- resource limits

Forbidden:
- kernel behavior flags
- path/mount/backend influencing kernel semantics
- “trust modes”
- “policy engines” inside runtime
