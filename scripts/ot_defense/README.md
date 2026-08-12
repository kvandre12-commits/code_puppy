# Defensive OT Exposure Audit

Tiny, boring, authorized-only scanner for water/OT environments.

It checks whether risky TCP services answer from the scan point. It does **not**
authenticate, exploit, fuzz, grab banners, or send protocol payloads.

## Why this exists

Recent water-sector compromises commonly involve exposed PLC/HMI or remote-access
surfaces with weak/default credentials. A frequent example is internet-reachable
Unitronics PLC programming access on TCP `20256`.

The point here is simple: find obvious exposure so operators can remove it.

## Usage

Dry-run plan:

```bash
python -m scripts.ot_defense.cli \
  --targets 192.0.2.10,192.0.2.11 \
  --i-am-authorized
```

Perform TCP connect checks:

```bash
python -m scripts.ot_defense.cli \
  --targets 192.0.2.0/29 \
  --i-am-authorized \
  --scan
```

Use a target file:

```bash
python -m scripts.ot_defense.cli \
  --target-file authorized_targets.txt \
  --i-am-authorized \
  --scan
```

Reports are written to `outputs/ot_defense/` as JSON and Markdown.

## Safety rails

- Requires `--i-am-authorized`.
- Defaults to dry-run unless `--scan` is present.
- Defaults to max `256` expanded hosts.
- TCP connect only, no payloads.
- IPv4 only for now, because YAGNI is a law not a suggestion.

## Default watched TCP ports

- `21` FTP
- `22` SSH
- `23` Telnet
- `80` HTTP admin/HMI
- `443` HTTPS admin/HMI
- `502` Modbus/TCP
- `3389` RDP
- `44818` EtherNet/IP
- `5900` VNC
- `8080` alternate web admin/HMI
- `20256` Unitronics PLC programming

## Immediate remediation guidance

If a risky OT/admin port is reachable from the public internet:

1. Remove direct internet exposure.
2. Require VPN + MFA + named accounts.
3. Segment IT and OT networks.
4. Rotate PLC/HMI/VPN/vendor credentials.
5. Validate controller logic against known-good backups.
6. Preserve logs and coordinate with CISA/FBI/EPA/WaterISAC if compromise is suspected.
