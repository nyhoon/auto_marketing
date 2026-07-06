"""NeoFall 홍보 배리에이션 로더 및 로테이션."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

VARIATIONS_PATH = Path(__file__).parent / "neofall_variations.json"


def load_variations() -> dict[str, Any]:
    if not VARIATIONS_PATH.exists():
        raise FileNotFoundError(f"배리에이션 파일 없음: {VARIATIONS_PATH}")
    return json.loads(VARIATIONS_PATH.read_text(encoding="utf-8"))


def get_angle_for_today(data: dict[str, Any] | None = None) -> str:
    payload = data or load_variations()
    weekday = datetime.now().weekday()
    order = payload["rotation"]["weekday_order"]
    return order[weekday % len(order)]


def list_angles(data: dict[str, Any] | None = None) -> dict[str, str]:
    payload = data or load_variations()
    return payload["angles"]


def get_variations_for_platform(
    platform: str,
    angle: str | None = None,
    data: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    payload = data or load_variations()
    items = payload["variations"].get(platform, [])
    if angle is None:
        return items
    return [item for item in items if item.get("angle") == angle]


def pick_variation(
    platform: str,
    angle: str | None = None,
    variation_id: str | None = None,
) -> dict[str, Any] | None:
    payload = load_variations()
    resolved_angle = angle or get_angle_for_today(payload)
    candidates = get_variations_for_platform(platform, resolved_angle, payload)

    if not candidates:
        candidates = get_variations_for_platform(platform, data=payload)

    if variation_id:
        for item in candidates:
            if item.get("id") == variation_id:
                return item
        return None

    if not candidates:
        return None

    day_index = datetime.now().timetuple().tm_yday
    return candidates[day_index % len(candidates)]


def variation_to_markdown(variation: dict[str, Any]) -> str:
    lines = variation.get("lines", [])
    title = variation.get("title", "")
    header = [
        f"<!-- angle: {variation.get('angle', '')} -->",
        f"<!-- id: {variation.get('id', '')} -->",
    ]
    if title:
        header.append(f"# {title}")
        header.append("")
    header.extend(lines)
    return "\n".join(header)


def export_variations_to_dir(
    output_dir: Path,
    angle: str | None = None,
    platforms: list[str] | None = None,
) -> list[str]:
    payload = load_variations()
    resolved_angle = angle or get_angle_for_today(payload)
    target_platforms = platforms or list(payload["variations"].keys())
    exported: list[str] = []

    for platform in target_platforms:
        variation = pick_variation(platform, angle=resolved_angle)
        if variation is None:
            continue
        content = variation_to_markdown(variation)
        file_path = output_dir / f"{platform}.md"
        file_path.write_text(content, encoding="utf-8")
        exported.append(platform)

    meta = {
        "angle": resolved_angle,
        "angle_label": payload["angles"].get(resolved_angle, resolved_angle),
        "exported_platforms": exported,
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    (output_dir / "variation_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return exported
