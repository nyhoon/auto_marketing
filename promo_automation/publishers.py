from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urljoin

import requests

from common import get_env_value, get_optional_env_value, has_platform_credentials


@dataclass(frozen=True)
class PublishResult:
    platform: str
    success: bool
    message: str
    external_id: str = ""


class PlatformPublisher(Protocol):
    platform: str

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        ...


class DiscordReviewNotifier:
    platform = "discord_review_notify"

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        platform_config = config["platforms"]["discord_review_notify"]
        webhook_env = platform_config["webhook_url_env"]
        webhook_url = get_env_value(webhook_env)

        payload = {"content": content[:1900]}
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code >= 400:
            return PublishResult(
                platform=self.platform,
                success=False,
                message=f"Discord 알림 실패: {response.status_code} {response.text}",
            )

        return PublishResult(
            platform=self.platform,
            success=True,
            message="Discord 검토 알림 전송 완료",
        )


class DiscordPublisher:
    platform = "discord"

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        platform_config = config["platforms"]["discord"]
        webhook_env = platform_config["webhook_url_env"]
        webhook_url = get_env_value(webhook_env)

        payload = {"content": content[:1900]}
        response = requests.post(webhook_url, json=payload, timeout=30)
        if response.status_code >= 400:
            return PublishResult(
                platform=self.platform,
                success=False,
                message=f"Discord 게시 실패: {response.status_code} {response.text}",
            )

        return PublishResult(
            platform=self.platform,
            success=True,
            message="Discord 공지 전송 완료",
        )


class XPublisher:
    platform = "x"

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        import tweepy

        platform_config = config["platforms"]["x"]
        client = tweepy.Client(
            consumer_key=get_env_value(platform_config["api_key_env"]),
            consumer_secret=get_env_value(platform_config["api_secret_env"]),
            access_token=get_env_value(platform_config["access_token_env"]),
            access_token_secret=get_env_value(platform_config["access_token_secret_env"]),
        )

        tweet_text = _extract_first_paragraph(content, max_length=280)
        response = client.create_tweet(text=tweet_text)
        tweet_id = str(response.data["id"]) if response.data else ""

        return PublishResult(
            platform=self.platform,
            success=True,
            message="X 게시 완료",
            external_id=tweet_id,
        )


class RedditPublisher:
    platform = "reddit"

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        import praw

        platform_config = config["platforms"]["reddit"]
        reddit = praw.Reddit(
            client_id=get_env_value(platform_config["client_id_env"]),
            client_secret=get_env_value(platform_config["client_secret_env"]),
            username=get_env_value(platform_config["username_env"]),
            password=get_env_value(platform_config["password_env"]),
            user_agent=platform_config.get("user_agent", "promo-automation/1.0"),
        )

        subreddit_name = platform_config["subreddits"][0]
        title, body = _split_title_and_body(content)
        submission = reddit.subreddit(subreddit_name).submit(title=title, selftext=body)

        return PublishResult(
            platform=self.platform,
            success=True,
            message=f"Reddit r/{subreddit_name} 게시 완료",
            external_id=submission.id,
        )


class WordPressPublisher:
    platform = "blog"

    def publish(self, content: str, config: dict[str, Any]) -> PublishResult:
        platform_config = config["platforms"]["blog"]
        blog_type = platform_config.get("type", "markdown_only")
        if blog_type == "markdown_only":
            return PublishResult(
                platform=self.platform,
                success=True,
                message="블로그는 markdown_only 모드입니다. 수동 게시용 파일만 생성됩니다.",
            )

        api_base_url = platform_config["api_base_url"].rstrip("/") + "/"
        token = get_env_value(platform_config["token_env"])
        title, body = _split_title_and_body(content)

        endpoint = urljoin(api_base_url, "wp-json/wp/v2/posts")
        response = requests.post(
            endpoint,
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json={
                "title": title,
                "content": body,
                "status": platform_config.get("post_status", "draft"),
            },
            timeout=30,
        )

        if response.status_code >= 400:
            return PublishResult(
                platform=self.platform,
                success=False,
                message=f"WordPress 게시 실패: {response.status_code} {response.text}",
            )

        post_id = str(response.json().get("id", ""))
        return PublishResult(
            platform=self.platform,
            success=True,
            message="WordPress 게시 완료",
            external_id=post_id,
        )


PUBLISHER_MAP = {
    "x": XPublisher(),
    "reddit": RedditPublisher(),
    "blog": WordPressPublisher(),
    "discord": DiscordPublisher(),
    "discord_review_notify": DiscordReviewNotifier(),
}


def publish_platform(
    platform: str,
    content: str,
    config: dict[str, Any],
    dry_run: bool,
) -> PublishResult:
    if dry_run:
        return PublishResult(
            platform=platform,
            success=True,
            message="dry-run 모드: 실제 게시는 하지 않았습니다.",
        )

    publisher = PUBLISHER_MAP.get(platform)
    if publisher is None:
        return PublishResult(
            platform=platform,
            success=False,
            message="자동 게시를 지원하지 않는 플랫폼입니다. 수동 게시가 필요합니다.",
        )

    if not has_platform_credentials(config, platform):
        return PublishResult(
            platform=platform,
            success=False,
            message="계정 정보 미설정 — .env 또는 GitHub Secrets를 확인하세요.",
        )

    return publisher.publish(content, config)


def save_publish_report(output_dir: Path, results: list[PublishResult]) -> Path:
    report_path = output_dir / "publish_report.json"
    payload = {
        "results": [
            {
                "platform": result.platform,
                "success": result.success,
                "message": result.message,
                "external_id": result.external_id,
            }
            for result in results
        ]
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def _split_title_and_body(content: str) -> tuple[str, str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    if not lines:
        return "업데이트 공지", content

    first_line = lines[0]
    if first_line.startswith("#"):
        title = first_line.lstrip("#").strip()
        body = "\n".join(lines[1:]).strip()
        return title, body or content

    return first_line[:120], content


def _extract_first_paragraph(content: str, max_length: int) -> str:
    paragraph = content.strip().split("\n\n")[0].replace("\n", " ").strip()
    if len(paragraph) <= max_length:
        return paragraph
    return paragraph[: max_length - 3] + "..."
