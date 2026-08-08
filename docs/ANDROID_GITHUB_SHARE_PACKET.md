# Android GitHub Share Packet

If you want to hand **your exact Code Puppy fork/branch** to another human,
stop making them reverse-engineer the install lane from six docs and a prayer.
Use the packet generator.

## What this is for

Use this when the question is:

> how do I put this exact Android-capable Code Puppy state on someone else's phone?

That means you need to hand them:

- the correct lane
- the exact repo URL
- the exact git ref or published version
- the copy-paste command
- the optional DroidPuppy overlay step
- the expected success shape

## Generate a packet for an exact fork/branch

From the repo root:

```bash
python scripts/make_android_handoff_packet.py \
  --lane checkout-ref \
  --repo-url https://github.com/yourname/code_puppy.git \
  --ref your-branch \
  --output outputs/android_handoff_packet.md
```

If you run it from a git checkout that already has a useful remote + branch, you
can let it infer those and just do:

```bash
python scripts/make_android_handoff_packet.py --output outputs/android_handoff_packet.md
```

That writes a Markdown packet you can paste into GitHub, Discord, Notes,
carrier pigeon, whatever.

## Generate a packet for the published artifact lane

If the thing you are sharing is the current published package instead of an
exact branch/ref, use:

```bash
python scripts/make_android_handoff_packet.py \
  --lane published-artifact \
  --published-version 0.0.569 \
  --output outputs/android_release_packet.md
```

## What the generated packet contains

- checkout-ref or published-artifact lane
- repo target and git ref when relevant
- exact `curl | bash` onboarding command
- expected proof shape
- optional DroidPuppy overlay attach commands
- a warning if your working tree is dirty

That last one matters because pretending a dirty local tree is already GitHub-shareable is just lying with extra romance.

## Recommended share order

1. share the packet
2. share the GitHub branch or tag
3. have the other human run the packet command in Termux
4. save the installer/onboarding output as the receipt
5. only then start talking about optional DroidPuppy-native depth

## Optional overlay reminder

Code Puppy is the engine + Android install surface.
DroidPuppy is the optional Android-native overlay.

Tell the story in that order unless you enjoy avoidable confusion.
