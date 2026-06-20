# Operation Zero

_Last updated: 2026-06-20_

Operation Zero is the closeout marker for the first live Project OS sandbox milestone
in this checkout.

## Final state

- Branch: `droidpuppy`
- Head: `0a46aaf`
- Working tree: clean
- Active supervisor services: `0`

## What landed

| Commit | Meaning |
| --- | --- |
| `9facec2` | Added Layer 4 `runtime: proot` support to `project_os_supervisor`, including rootfs init, bind-mount launch wrapping, CLI `init-sandbox`, and tool `project_os_supervisor_init_sandbox`. |
| `0a46aaf` | Hardened live Alpine minirootfs handling so absolute symlinks do not break extraction fallback or rootfs initialization checks. |

## What was proven live on-device

The Termux package `proot` was installed and used for a real smoke run on Android.

The live smoke verified all of the following:

1. Alpine aarch64 minirootfs downloaded and initialized successfully.
2. A supervisor-managed service with `runtime: proot` launched for real.
3. Host event-bus passthrough worked from inside the sandbox.
4. The guest process wrote heartbeat payloads to the supervisor heartbeat file.
5. The guest process published three `system.sandbox` `sandbox_heartbeat` events.
6. The sandbox smoke service exited with code `0`.
7. The event-bus and supervisor state were shut down cleanly afterward.

## Key artifacts

These files are runtime evidence, not stable source:

- `outputs/project_os_proot_smoke_manifest_20260620T163315Z.json`
- `outputs/project_os_init_sandbox_20260620T163551Z.json`
- `outputs/project_os_smoke_start_20260620T163551Z.json`
- `outputs/project_os_proot_smoke_tail_20260620T163551Z.json`

The tail artifact contains the cleanest proof of guest-to-host publication:

```text
[system.sandbox] ... sandbox_heartbeat source=isolated-smoke :: sandbox beat=1
[system.sandbox] ... sandbox_heartbeat source=isolated-smoke :: sandbox beat=2
[system.sandbox] ... sandbox_heartbeat source=isolated-smoke :: sandbox beat=3
```

## Important implementation note

Alpine minirootfs uses absolute symlinks such as `/bin/sh -> /bin/busybox`.
That is normal inside the guest and must not be mistaken for a broken rootfs by
host-side validation.

## Source of truth

Stable implementation lives in:

```text
code_puppy/plugins/project_os_supervisor/
```

Generated proof lives in:

```text
outputs/
```

Treat the source tree as the product and the output artifacts as receipts.

## Next sensible move

If this line of work continues, the next step is not to re-prove Layer 4.
The next step is to build upward from it: richer sandbox service templates,
stronger authority coupling, and clearer operator workflows for isolated jobs.
