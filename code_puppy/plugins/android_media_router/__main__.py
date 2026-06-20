from __future__ import annotations

import argparse
import json

from .tooling import handle_transcript, listen_loop, set_favorite, sharpedge_play


def main() -> None:
    parser = argparse.ArgumentParser(description="SharpEdge Android media router")
    parser.add_argument(
        "--say", help="Test with typed transcript instead of microphone"
    )
    parser.add_argument(
        "--query", help="Play a direct query without transcript parsing"
    )
    parser.add_argument("--provider", default="auto")
    parser.add_argument("--favorite", action="store_true")
    parser.add_argument("--set-favorite", help="Save a favorite song target")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    parser.add_argument("--max-listens", type=int)
    parser.add_argument("--sleep", type=float, default=1.0)
    parser.add_argument("--quiet-beep", action="store_true")
    parser.add_argument("--stop-after-action", action="store_true")
    parser.add_argument("--music-volume", type=int, default=12)
    parser.add_argument("--no-press-play", action="store_true")
    parser.add_argument("--dry-run", action="store_true", default=True)
    parser.add_argument(
        "--execute", action="store_true", help="Actually launch Android intents"
    )
    args = parser.parse_args()

    dry_run = not args.execute
    if args.loop:
        raise SystemExit(
            listen_loop(
                dry_run=dry_run,
                timeout_seconds=args.timeout,
                quiet_beep=args.quiet_beep,
                stop_after_action=args.stop_after_action,
                max_listens=args.max_listens,
                music_volume=args.music_volume,
                sleep_seconds=args.sleep,
            )
        )

    if args.set_favorite:
        result = set_favorite(
            args.set_favorite, provider=args.provider, dry_run=dry_run
        )
    elif args.say:
        result = handle_transcript(
            args.say, dry_run=dry_run, music_volume=args.music_volume
        )
    else:
        result = sharpedge_play(
            query=args.query or "",
            provider=args.provider,
            favorite=args.favorite,
            dry_run=dry_run,
            music_volume=args.music_volume,
            press_play=not args.no_press_play,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    raise SystemExit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
