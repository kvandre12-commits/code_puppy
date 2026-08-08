# Private Operator Channel

This is the grown-up version of remote control:

- **your devices**
- **your private network path**
- **your auth boundary**
- **your audit log**

Not Discord. Not a webhook taped to somebody else's hallway.

## What this plugin does

The builtin plugin at `code_puppy/plugins/private_operator_channel/` provides:

- a status tool: `private_operator_channel_status`
- an example config writer: `private_operator_channel_write_example_config`
- a signed-request builder: `private_operator_channel_sign_request`
- a tiny stdlib HTTP control server with optional TLS + client-cert auth:

```bash
python -m code_puppy.plugins.private_operator_channel --config ~/.code_puppy/private_operator_channel.json
```

## Safety posture

This is intentionally narrow.

### Read-only actions

- `ping`
- `status`
- `authority_status`
- `bus_status`
- `tail_bus`

### Bounded Android action

- `android_open`

Even that one is constrained by config:

- target must be in `allowed_android_targets`
- effectful opens are denied unless `allow_effectful_actions=true`
- `dry_run=true` remains available for previews

No arbitrary shell. No raw intent firehose. No fake stealth nonsense.

## Recommended deployment

Use this over a private overlay network such as:

- Tailscale
- WireGuard

Bind the server to:

- `127.0.0.1` for local-only testing, or
- a **private overlay IP** for multi-device access

Do **not** bind this to `0.0.0.0` on the public internet unless you enjoy bad decisions.

### Tailscale/WireGuard-first recommendation

For the real grown-up path:

1. join the phone / laptop / server to the same private overlay
2. bind the service to the overlay IP, not the public interface
3. enable `tls_enabled`
4. provide `tls_certfile` + `tls_keyfile`
5. set `require_client_certificate=true` with `tls_client_cafile`
6. keep the shared-secret signature too, because defense in depth is cute when it's useful

## Quick start

### 1. Write the starter config

Inside Code Puppy, call:

- `private_operator_channel_write_example_config()`

or directly create:

```bash
python - <<'PY'
from code_puppy.plugins.private_operator_channel.config import write_example_config
print(write_example_config(overwrite=False))
PY
```

Default path:

```text
~/.code_puppy/private_operator_channel.json
```

### 2. Set the shared secret

```bash
export PRIVATE_OPERATOR_CHANNEL_SECRET='replace-me-with-a-long-random-secret'
```

### 3. Edit the config

Set:

- `bind_host`
- `port`
- `allow_effectful_actions`
- `allowed_android_targets`
- `tls_enabled`
- `tls_certfile`
- `tls_keyfile`
- `tls_client_cafile`
- `require_client_certificate`

### 4. Start the server

```bash
python -m code_puppy.plugins.private_operator_channel --config ~/.code_puppy/private_operator_channel.json
```

### 5. Build a signed request

Inside Code Puppy, use:

- `private_operator_channel_sign_request(action='status')`

Or directly in Python:

```bash
python - <<'PY'
import json, os
from code_puppy.plugins.private_operator_channel.runtime import build_signed_request
payload = build_signed_request(
    action='status',
    args={'include_authority': True},
    shared_secret=os.environ['PRIVATE_OPERATOR_CHANNEL_SECRET'],
)
print(json.dumps(payload))
PY
```

### 6. Send it

Tiny client script:

```bash
python scripts/private_operator_channel_client.py \
  --url http://127.0.0.1:8766/v1/control \
  --action status \
  --shared-secret "$PRIVATE_OPERATOR_CHANNEL_SECRET"
```

Or with curl:

```bash
curl -sS http://127.0.0.1:8766/v1/control \
  -H 'content-type: application/json' \
  --data @request.json
```

If you move to HTTPS + client certificates, the tiny client also supports:

- `--ca-file`
- `--client-cert`
- `--client-key`

## Audit

Every handled request appends a JSONL row to:

```text
outputs/private_operator_channel_audit.jsonl
```

That keeps a local operator trail without outsourcing the transport path.

## Next obvious upgrade

If you want to harden this further, the next step is:

- replace shared-secret auth with device keypairs
- require approval-receipt / lease context for effectful actions
- bind only on a Tailscale/WireGuard address
- move from optional client-cert auth to mandatory overlay-only mTLS everywhere
