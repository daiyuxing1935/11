"""Validate that every configured resource illustration is deployable."""

from __future__ import annotations

import json
from pathlib import Path


DATA_DIR = Path(__file__).resolve().parent / "data"
CONFIG_PATH = DATA_DIR / "resource_image_config.json"
IMAGES_DIR = DATA_DIR / "generated_images"


def main() -> None:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    available = {path.stem for path in IMAGES_DIR.glob("*.svg")}
    missing = {
        resource_id: [image_hash for image_hash in hashes if image_hash not in available]
        for resource_id, hashes in config.items()
    }
    missing = {resource_id: hashes for resource_id, hashes in missing.items() if hashes}

    if missing:
        details = "; ".join(
            f"{resource_id}: {', '.join(hashes)}"
            for resource_id, hashes in sorted(missing.items())
        )
        raise SystemExit(f"Missing configured resource SVG files: {details}")

    print(f"Validated {sum(map(len, config.values()))} configured resource SVG references")


if __name__ == "__main__":
    main()
