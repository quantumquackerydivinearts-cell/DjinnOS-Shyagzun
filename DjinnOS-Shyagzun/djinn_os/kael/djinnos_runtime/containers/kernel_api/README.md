# Kael Cluster: kernel_api (containers)

This cluster runs the Shygazun Kernel HTTP surface in a container.

Non-negotiables:
- Deployment context must not alter kernel semantics.
- No filesystem path semantics.
- No “sanctum mode”, “atelier mode”, or runtime flags that affect causality.

Run:
- docker compose up --build

Expose:
- host port -> container 8080
