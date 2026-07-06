"""무료 홍보 파이프라인 — AI/API 비용 없음."""

from __future__ import annotations

import argparse
from pathlib import Path

from analyze_metrics import build_weekly_report
from common import create_output_bundle, is_free_mode, load_config, resolve_release_info, write_json
from variation_loader import export_variations_to_dir, get_angle_for_today, list_angles


def write_manual_checklist(output_dir: Path, config: dict) -> None:
    play_url = config["app"].get("play_store_url", "")
    content = "\n".join([
        "# 수동 게시 체크리스트 (무료 모드)",
        "",
        "- [ ] **Google Play** — `google_play.md` → Play Console 변경사항",
        "- [ ] **X** — `x.md` 복사 → 직접 트윗",
        "- [ ] **Threads** — `threads.md` 복사 → 앱에서 게시",
        "- [ ] **Reddit** — `reddit.md` 복사 → 서브레딧에 게시",
        "- [ ] **Discord** — `discord.md` 복사 → 서버 공지",
        "- [ ] **YouTube Shorts** — `youtube_shorts.md` 대본 → 영상 촬영·업로드",
        "- [ ] **TikTok** — `tiktok.md` 대본 → 직접 업로드",
        "- [ ] **블로그** — `blog.md` → 블로그에 붙여넣기",
        "",
        f"Play Store: {play_url}",
        "",
        "## 권장 순서",
        "1. Play → 2. X/Threads → 3. Reddit → 4. Shorts/TikTok → 5. 블로그",
    ])
    (output_dir / "manual_publish_checklist.md").write_text(content, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="무료 홍보 파이프라인 (AI/API 비용 0원)")
    parser.add_argument("--angle", default="", help="홍보 각도 (미지정 시 오늘 요일)")
    parser.add_argument("--list-angles", action="store_true", help="각도 목록")
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
    write_manual_checklist(bundle.directory, config)

    report = build_weekly_report(config, bundle.directory)
    write_json(bundle.directory / "kpi_report.json", report)

    print("[INFO] === 무료 모드 완료 (비용 0원) ===")
    print(f"[INFO] 각도: {resolved_angle}")
    print(f"[INFO] 플랫폼: {', '.join(platform_list)}")
    print(f"[INFO] 출력: {bundle.directory.resolve()}")
    print("[INFO] manual_publish_checklist.md 를 보고 수동 게시하세요.")


if __name__ == "__main__":
    main()
