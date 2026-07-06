"""무료 홍보 파이프라인 — 문구 생성 + 무료 자동 게시(Discord/Reddit)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from analyze_metrics import build_weekly_report
from common import (
    create_output_bundle,
    get_auto_publish_platforms,
    load_config,
    write_json,
)
from publish_posts import publish_all
from variation_loader import export_variations_to_dir, get_angle_for_today, list_angles

MANUAL_PLATFORMS = (
    "google_play",
    "x",
    "threads",
    "youtube_shorts",
    "tiktok",
    "blog",
)


def write_publish_checklist(output_dir: Path, config: dict, auto_published: list[str]) -> None:
    play_url = config["app"].get("play_store_url", "")
    lines = [
        "# 게시 체크리스트",
        "",
        "## 자동 게시 완료",
    ]

    if auto_published:
        lines.extend(f"- [x] **{platform}** (자동)" for platform in auto_published)
    else:
        lines.append("- (없음 - Discord/Reddit 계정 설정 필요)")

    lines.extend(["", "## 수동 게시 필요 (API 무료 자동화 불가)"])
    for platform in MANUAL_PLATFORMS:
        lines.append(f"- [ ] **{platform}** - `{platform}.md` 참고")

    lines.extend([
        "",
        f"Play Store: {play_url}",
        "",
        "## 수동 권장 순서",
        "1. Google Play → 2. X/Threads → 3. Shorts/TikTok → 4. 블로그",
    ])
    (output_dir / "manual_publish_checklist.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="무료 홍보 + 자동 게시")
    parser.add_argument("--angle", default="", help="홍보 각도 (미지정 시 오늘 요일)")
    parser.add_argument("--list-angles", action="store_true", help="각도 목록")
    parser.add_argument("--publish", action="store_true", help="Discord/Reddit 자동 게시")
    parser.add_argument("--approve", action="store_true", help="자동 게시 승인 (필수)")
    parser.add_argument("--dry-run", action="store_true", help="게시 시뮬레이션만")
    args = parser.parse_args()

    if args.list_angles:
        for code, label in list_angles().items():
            print(f"  {code}: {label}")
        return

    config = load_config()
    angle = args.angle or None
    bundle = create_output_bundle(config)
    platform_list = export_variations_to_dir(bundle.directory, angle=angle)
    resolved_angle = angle or get_angle_for_today()

    write_json(
        bundle.directory / "summary.json",
        {
            "timestamp": bundle.timestamp,
            "mode": "free",
            "angle": resolved_angle,
            "platforms": platform_list,
            "cost": "0원",
        },
    )

    auto_published: list[str] = []

    if args.publish:
        if not args.approve and not args.dry_run:
            print("[ERROR] 자동 게시는 --approve 플래그가 필요합니다.")
            sys.exit(1)

        auto_targets = get_auto_publish_platforms(config)
        if not auto_targets:
            print("[WARN] 자동 게시 대상 없음 - .env에 Discord/Reddit 계정을 설정하세요.")
        else:
            print(f"[INFO] 자동 게시 대상: {', '.join(auto_targets)}")
            results = publish_all(
                config,
                bundle.directory,
                dry_run=args.dry_run,
                platform_filter=auto_targets,
            )
            auto_published = [
                result.platform for result in results if result.success
            ]

    write_publish_checklist(bundle.directory, config, auto_published)

    report = build_weekly_report(config, bundle.directory)
    write_json(bundle.directory / "kpi_report.json", report)

    print("[INFO] === 무료 모드 완료 ===")
    print(f"[INFO] 각도: {resolved_angle}")
    print(f"[INFO] 문구 생성: {', '.join(platform_list)}")
    if auto_published:
        print(f"[INFO] 자동 게시: {', '.join(auto_published)}")
    print(f"[INFO] 출력: {bundle.directory.resolve()}")


if __name__ == "__main__":
    main()
