from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from common import find_latest_output_dir, load_config, write_json


def build_weekly_report(config: dict, output_dir: Path) -> dict:
    app_name = config["app"].get("name", "앱")
    summary_path = output_dir / "summary.json"
    publish_report_path = output_dir / "publish_report.json"

    summary = {}
    publish_report = {"results": []}

    if summary_path.exists():
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    if publish_report_path.exists():
        publish_report = json.loads(publish_report_path.read_text(encoding="utf-8"))

    success_count = sum(1 for item in publish_report["results"] if item.get("success"))
    fail_count = len(publish_report["results"]) - success_count

    return {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "app_name": app_name,
        "release_title": summary.get("release_title", ""),
        "generated_platforms": summary.get("platforms", []),
        "publish_success_count": success_count,
        "publish_fail_count": fail_count,
        "kpi_targets": config.get("kpi", {}),
        "next_actions": [
            "노출이 낮은 플랫폼은 톤/길이를 조정해 다음 릴리스에 반영",
            "클릭률이 낮으면 첫 문장(후킹)만 강화",
            "댓글이 있는 채널은 24시간 내 답변",
            "YouTube/TikTok은 첫 3초 장면 A/B 테스트",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="홍보 KPI 리포트 생성")
    parser.add_argument("--output-dir", default="", help="특정 generated 폴더 경로")
    args = parser.parse_args()

    config = load_config()
    output_dir = find_latest_output_dir(config) if not args.output_dir else Path(args.output_dir)

    report = build_weekly_report(config, output_dir)
    report_path = output_dir / "kpi_report.json"
    write_json(report_path, report)

    markdown_lines = [
        "# 주간 홍보 리포트",
        "",
        f"- 앱: {report['app_name']}",
        f"- 릴리스: {report['release_title']}",
        f"- 생성 플랫폼: {', '.join(report['generated_platforms']) or '없음'}",
        f"- 자동 발행 성공/실패: {report['publish_success_count']}/{report['publish_fail_count']}",
        "",
        "## 다음 개선 액션",
    ]
    markdown_lines.extend(f"- {action}" for action in report["next_actions"])

    markdown_path = output_dir / "kpi_report.md"
    markdown_path.write_text("\n".join(markdown_lines), encoding="utf-8")

    print(f"[INFO] KPI 리포트 생성: {report_path}")
    print(f"[INFO] KPI 요약: {markdown_path}")


if __name__ == "__main__":
    main()
