from __future__ import annotations

import argparse
import sys

from analyze_metrics import build_weekly_report
from common import find_latest_output_dir, load_config, resolve_release_info, write_json
from generate_posts import generate_all_posts
from n8n_bridge import notify_n8n
from publish_posts import notify_review, publish_all


def run_generate(config: dict) -> tuple:
    release = resolve_release_info(config)
    config["github"]["release_tag"] = release.tag
    config["github"]["release_title"] = release.title
    config["github"]["release_body"] = release.body
    return generate_all_posts(config)


def run_publish(config: dict, output_dir, dry_run: bool) -> None:
    publish_all(config, output_dir, dry_run=dry_run)


def run_analyze(config: dict, output_dir) -> None:
    report = build_weekly_report(config, output_dir)
    write_json(output_dir / "kpi_report.json", report)


def main() -> None:
    parser = argparse.ArgumentParser(description="앱 홍보 자동화 파이프라인")
    parser.add_argument("--generate", action="store_true", help="초안 생성")
    parser.add_argument("--notify", action="store_true", help="Discord 검토 알림")
    parser.add_argument("--publish", action="store_true", help="API 지원 채널 발행")
    parser.add_argument("--analyze", action="store_true", help="KPI 리포트 생성")
    parser.add_argument("--approve", action="store_true", help="검토 승인 후 발행 허용")
    parser.add_argument("--dry-run", action="store_true", help="실제 API 호출 없이 실행")
    parser.add_argument("--all", action="store_true", help="generate + notify + analyze")
    parser.add_argument("--angle", default="", help="홍보 각도 (ranking_challenge, user_review 등)")
    parser.add_argument("--use-variations", action="store_true", help="AI 대신 neofall_variations.json 사용")
    args = parser.parse_args()

    if not any([args.generate, args.notify, args.publish, args.analyze, args.all]):
        args.all = True

    config = load_config()

    output_bundle = None
    platform_list: list[str] = []

    if args.generate or args.all:
        if args.use_variations:
            from common import create_output_bundle, write_json
            from variation_loader import export_variations_to_dir, get_angle_for_today

            angle = args.angle or None
            output_bundle = create_output_bundle(config)
            platform_list = export_variations_to_dir(output_bundle.directory, angle=angle)
            write_json(
                output_bundle.directory / "summary.json",
                {
                    "timestamp": output_bundle.timestamp,
                    "mode": "variation_export",
                    "angle": angle or get_angle_for_today(),
                    "platforms": platform_list,
                },
            )
            print(f"[INFO] 배리에이션보내기 완료: {', '.join(platform_list)}")
        else:
            output_bundle, platform_list = run_generate(config)

    if output_bundle is None:
        output_bundle_dir = find_latest_output_dir(config)
    else:
        output_bundle_dir = output_bundle.directory

    release = resolve_release_info(config)

    if args.notify or args.all:
        notify_review(config, output_bundle_dir, release, platform_list, dry_run=args.dry_run)
        notify_n8n(output_bundle_dir, release, platform_list, config)

    if args.publish:
        if not args.approve and not args.dry_run:
            print("[ERROR] 실제 발행은 --approve 플래그가 필요합니다.")
            sys.exit(1)
        run_publish(config, output_bundle_dir, dry_run=args.dry_run)

    if args.analyze or args.all:
        run_analyze(config, output_bundle_dir)

    print("[INFO] 파이프라인 실행 완료")


if __name__ == "__main__":
    main()
