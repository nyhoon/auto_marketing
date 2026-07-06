from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    PUBLISHABLE_PLATFORMS,
    find_latest_output_dir,
    get_auto_publish_platforms,
    has_platform_credentials,
    is_platform_enabled,
    load_config,
    read_platform_content,
    resolve_release_info,
)
from compliance import record_publish, run_all_checks
from publishers import publish_platform, save_publish_report


def build_review_message(output_dir, release, platform_list: list[str]) -> str:
    lines = [
        "📣 앱 홍보 초안 생성 완료",
        f"릴리스: {release.title or release.tag}",
        f"폴더: {output_dir.name}",
        "",
        "생성된 플랫폼:",
    ]
    lines.extend(f"- {platform}" for platform in platform_list)
    lines.extend(
        [
            "",
            "검토 후 발행 명령:",
            "`python promo_automation/run_pipeline.py --publish --approve`",
            "",
            "자동 게시 가능: x, reddit, blog, discord",
            "수동 게시 필요: google_play, threads, youtube_shorts, tiktok",
        ]
    )
    return "\n".join(lines)


def publish_all(config: dict, output_dir, dry_run: bool, platform_filter: list[str] | None = None) -> list:
    results = []
    all_contents: dict[str, str] = {}

    target_platforms = platform_filter or [
        platform
        for platform in PUBLISHABLE_PLATFORMS
        if is_platform_enabled(config, platform)
    ]

    for platform in target_platforms:
        try:
            all_contents[platform] = read_platform_content(output_dir, platform)
        except FileNotFoundError:
            print(f"[SKIP] {platform}: 초안 파일 없음")

    for platform in target_platforms:
        if platform not in all_contents:
            continue

        if not has_platform_credentials(config, platform):
            from publishers import PublishResult
            results.append(PublishResult(
                platform=platform,
                success=False,
                message="계정 미설정 — .env에 키 추가 후 다시 실행",
            ))
            print(f"[SKIP] {platform}: 계정 정보 없음")
            continue

        content = all_contents[platform]
        compliance = run_all_checks(platform, content, all_contents, config)

        if not compliance.passed:
            for violation in compliance.violations:
                print(f"[BLOCKED] {platform}: {violation}")
            from publishers import PublishResult
            results.append(PublishResult(
                platform=platform,
                success=False,
                message=f"compliance 실패: {'; '.join(compliance.violations)}",
            ))
            continue

        result = publish_platform(platform, content, config, dry_run=dry_run)
        results.append(result)

        if result.success and not dry_run:
            record_publish(platform, result.external_id)

        status = "OK" if result.success else "FAIL"
        print(f"[{status}] {platform}: {result.message}")

    save_publish_report(output_dir, results)
    return results


def notify_review(config: dict, output_dir, release, platform_list: list[str], dry_run: bool) -> None:
    if not is_platform_enabled(config, "discord_review_notify"):
        print("[INFO] discord_review_notify 비활성화: 검토 알림 생략")
        return

    message = build_review_message(output_dir, release, platform_list)
    result = publish_platform("discord_review_notify", message, config, dry_run=dry_run)
    status = "OK" if result.success else "FAIL"
    print(f"[{status}] review notify: {result.message}")


def main() -> None:
    parser = argparse.ArgumentParser(description="생성된 초안 발행")
    parser.add_argument("--output-dir", default="", help="특정 generated 폴더 경로")
    parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 시뮬레이션")
    parser.add_argument("--notify-only", action="store_true", help="검토 알림만 전송")
    args = parser.parse_args()

    config = load_config()
    release = resolve_release_info(config)
    output_dir = find_latest_output_dir(config) if not args.output_dir else Path(args.output_dir)

    summary_path = output_dir / "summary.json"
    platform_list: list[str] = []
    if summary_path.exists():
        platform_list = json.loads(summary_path.read_text(encoding="utf-8")).get("platforms", [])

    if args.notify_only:
        notify_review(config, output_dir, release, platform_list, dry_run=args.dry_run)
        return

    publish_all(config, output_dir, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
