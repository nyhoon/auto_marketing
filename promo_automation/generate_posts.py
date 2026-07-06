from __future__ import annotations

import argparse
import json
from typing import Any

from common import (
    CONTENT_PLATFORMS,
    ReleaseInfo,
    create_output_bundle,
    get_env_value,
    is_platform_enabled,
    load_config,
    load_guide_text,
    resolve_release_info,
    write_json,
)
from platform_rules import PLATFORM_PROMPT_RULES


def get_openai_client(config: dict[str, Any]):
    api_key_env = config["openai"]["api_key_env"]
    api_key = get_env_value(api_key_env)

    from openai import OpenAI

    return OpenAI(api_key=api_key)


def build_prompt_for_platform(
    platform: str,
    guide_text: str,
    release: ReleaseInfo,
    app_config: dict[str, Any],
) -> str:
    app_name = app_config.get("name", "앱")
    app_description = app_config.get("description", "")
    play_store_url = app_config.get("play_store_url", "")
    keywords = ", ".join(app_config.get("keywords", []))

    base_instruction = (
        "당신은 모바일 앱 마케터입니다. "
        "아래 운영 가이드 원칙을 반드시 지키면서, 지정된 플랫폼에 맞는 홍보 글 초안을 작성하세요. "
        "동일한 글을 여러 플랫폼에 복붙하지 말고, 플랫폼 문화와 톤에 맞게 변형하세요. "
        "과장 광고, 허위 리뷰 유도, 스팸성 문구는 금지입니다."
    )

    angle_hint = app_config.get("promo_angle", "")
    angle_instruction = ""
    if angle_hint:
        angle_instruction = (
            f"\n이번 홍보 각도: {angle_hint}\n"
            "위 각도에 맞게 톤과 메시지를 집중하되, 플랫폼 규칙은 반드시 지키세요."
        )

    platform_instruction_map = {
        "google_play": (
            "플랫폼: Google Play 변경사항\n"
            f"{PLATFORM_PROMPT_RULES['google_play']}"
        ),
        "reddit": (
            "플랫폼: Reddit\n"
            f"{PLATFORM_PROMPT_RULES['reddit']}"
        ),
        "x": (
            "플랫폼: X\n"
            f"{PLATFORM_PROMPT_RULES['x']}"
        ),
        "threads": (
            "플랫폼: Threads\n"
            f"{PLATFORM_PROMPT_RULES['threads']}"
        ),
        "youtube_shorts": (
            "플랫폼: YouTube Shorts\n"
            f"{PLATFORM_PROMPT_RULES['youtube_shorts']}"
        ),
        "tiktok": (
            "플랫폼: TikTok\n"
            f"{PLATFORM_PROMPT_RULES['tiktok']}"
        ),
        "discord": (
            "플랫폼: Discord\n"
            f"{PLATFORM_PROMPT_RULES['discord']}"
        ),
        "blog": (
            "플랫폼: 블로그(SEO)\n"
            f"{PLATFORM_PROMPT_RULES['blog']}"
        ),
    }

    return (
        f"{base_instruction}\n"
        f"{angle_instruction}\n\n"
        f"{platform_instruction_map[platform]}\n\n"
        "=== 앱 정보 ===\n"
        f"앱 이름: {app_name}\n"
        f"앱 설명: {app_description}\n"
        f"Play Store URL: {play_store_url}\n"
        f"키워드: {keywords}\n"
        f"릴리스 태그: {release.tag}\n"
        f"릴리스 제목: {release.title}\n"
        f"릴리스 변경사항:\n{release.body}\n\n"
        "=== 운영 가이드 ===\n"
        f"{guide_text}\n"
    )


def generate_for_platform(
    client: Any,
    model: str,
    platform: str,
    guide_text: str,
    release: ReleaseInfo,
    app_config: dict[str, Any],
) -> str:
    prompt = build_prompt_for_platform(platform, guide_text, release, app_config)
    completion = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "당신은 앱 마케팅 카피라이터입니다."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.7,
    )
    return completion.choices[0].message.content.strip()


def generate_all_posts(config: dict[str, Any]) -> tuple[Any, list[str]]:
    guide_text = load_guide_text()
    client = get_openai_client(config)
    model = config["openai"]["model"]
    release = ReleaseInfo(
        tag=config["github"].get("release_tag", ""),
        title=config["github"].get("release_title", ""),
        body=config["github"].get("release_body", ""),
    )
    app_config = config["app"]
    output_bundle = create_output_bundle(config)

    generated_platform_list: list[str] = []

    for platform in CONTENT_PLATFORMS:
        if not is_platform_enabled(config, platform):
            continue

        print(f"[INFO] {platform} 초안 생성 중...")
        content = generate_for_platform(
            client=client,
            model=model,
            platform=platform,
            guide_text=guide_text,
            release=release,
            app_config=app_config,
        )

        platform_file = output_bundle.directory / f"{platform}.md"
        platform_file.write_text(content, encoding="utf-8")
        generated_platform_list.append(platform)

    write_json(
        output_bundle.directory / "summary.json",
        {
            "timestamp": output_bundle.timestamp,
            "release_tag": release.tag,
            "release_title": release.title,
            "release_body": release.body,
            "platforms": generated_platform_list,
        },
    )

    manual_checklist = _build_manual_checklist(generated_platform_list, config)
    (output_bundle.directory / "manual_publish_checklist.md").write_text(
        manual_checklist,
        encoding="utf-8",
    )

    print(f"[INFO] 생성 완료: {', '.join(generated_platform_list)}")
    print(f"[INFO] 출력 폴더: {output_bundle.directory.resolve()}")
    return output_bundle, generated_platform_list


def _build_manual_checklist(platform_list: list[str], config: dict[str, Any]) -> str:
    manual_platform_map = {
        "google_play": "Play Console > 출시 > 프로덕션 > 새 버전 > 변경사항에 붙여넣기",
        "threads": "Threads 앱에서 직접 게시 (API 제한)",
        "youtube_shorts": "YouTube Studio > Shorts 업로드 (대본 참고)",
        "tiktok": "TikTok 앱에서 직접 업로드 (대본 참고)",
    }

    lines = [
        "# 수동 게시 체크리스트",
        "",
        "자동 게시가 불가능하거나 검토가 필요한 채널입니다.",
        "",
    ]

    for platform in platform_list:
        if platform in manual_platform_map:
            lines.append(f"- [ ] **{platform}**: {manual_platform_map[platform]}")

    lines.extend(
        [
            "",
            "## 권장 게시 순서",
            "1. Google Play 변경사항 반영",
            "2. 블로그",
            "3. X / Threads",
            "4. Reddit",
            "5. Discord",
            "6. YouTube Shorts / TikTok",
            "",
            f"Play Store: {config['app'].get('play_store_url', '')}",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="플랫폼별 홍보 초안 생성")
    parser.parse_args()

    config = load_config()
    release = resolve_release_info(config)
    config["github"]["release_tag"] = release.tag
    config["github"]["release_title"] = release.title
    config["github"]["release_body"] = release.body

    generate_all_posts(config)


if __name__ == "__main__":
    main()
