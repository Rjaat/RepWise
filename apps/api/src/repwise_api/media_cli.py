from __future__ import annotations

import argparse
import json
from pathlib import Path

from repwise_api.media import MediaPreflightError, normalize_media


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and normalize RepWise media")
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    try:
        result = normalize_media(args.source, args.destination, args.sha256)
    except MediaPreflightError as error:
        print(
            json.dumps(
                {"status": "rejected", "code": error.code, "message": str(error)}
            )
        )
        return 1
    manifest = json.dumps(result.to_dict(), indent=2, sort_keys=True)
    if args.manifest:
        args.manifest.write_text(f"{manifest}\n", encoding="utf-8")
    else:
        print(manifest)
    return 0


if __name__ == "__main__":  # pragma: no cover - exercised as a process
    raise SystemExit(main())
