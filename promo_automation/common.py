from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"
GUIDE_PATH = BASE_DIR.parent / "앱_홍보_자동화_운영_가이드.md"


def _load_dotenv() -> None:
    try:
        from dotenv import load_dotenv

        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
    except ImportError:
        pass


_load_dotenv()

CONTENT_PLATFORMS = (
    "google_play",
    "reddit",
    "x",
    "threads",
    "youtube_shorts",
    "tiktok",
    "discord",
    "blog",
)

PUBLISHABLE_PLATFORMS = (
    "x",
    "reddit",
    "blog",
    "discord",
)


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    title: str
    body: str


@dataclass(frozen=True)
class OutputBundle:
    timestamp: str
    directory: Path


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"config.json이 없습니다. config.example.json을 복사해 만드세요: {CONFIG_PATH}"
        )
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_config(config: dict[str, Any]) -> None:
    with CONFIG_PATH.open("w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def load_guide_text() -> str:
    if not GUIDE_PATH.exists():
        return ""
    return GUIDE_PATH.read_text(encoding="utf-8")


def get_env_value(env_name: str) -> str:
    value = os.getenv(env_name, "").strip()
    if not value:
        raise EnvironmentError(f"{env_name} 환경 변수가 설정되지 않았습니다.")
    return value


def get_optional_env_value(env_name: str) -> str:
    return os.getenv(env_name, "").strip()


def resolve_release_info(config: dict[str, Any]) -> ReleaseInfo:
    github_config = config["github"]
    title = github_config.get("release_title", "").strip()
    body = github_config.get("release_body", "").strip()
    tag = github_config.get("release_tag", "").strip()

    if not title:
        title = get_optional_env_value("RELEASE_TITLE")
    if not body:
        body = get_optional_env_value("RELEASE_BODY")
    if not tag:
        tag = get_optional_env_value("RELEASE_TAG")

    if not title and not body:
        app_name = config.get("app", {}).get("name", "NeoFall")
        title = f"{app_name} 홍보"
        body = config.get("app", {}).get("description", "")

    return ReleaseInfo(tag=tag, title=title, body=body)


def is_free_mode(config: dict[str, Any]) -> bool:
    return config.get("workflow", {}).get("mode", "free") == "free"


def create_output_bundle(config: dict[str, Any]) -> OutputBundle:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_base = Path(config["output"]["base_dir"])
    if not output_base.is_absolute():
        output_base = BASE_DIR.parent / output_base
    output_dir = output_base / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return OutputBundle(timestamp=timestamp, directory=output_dir)


def find_latest_output_dir(config: dict[str, Any]) -> Path:
    output_base = Path(config["output"]["base_dir"])
    if not output_base.is_absolute():
        output_base = BASE_DIR.parent / output_base
    if not output_base.exists():
        raise FileNotFoundError(f"생성된 결과가 없습니다: {output_base}")

    candidates = [path for path in output_base.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"생성된 결과 폴더가 없습니다: {output_base}")

    return sorted(candidates)[-1]


def read_platform_content(output_dir: Path, platform: str) -> str:
    platform_file = output_dir / f"{platform}.md"
    if not platform_file.exists():
        raise FileNotFoundError(f"{platform} 초안 파일이 없습니다: {platform_file}")
    return platform_file.read_text(encoding="utf-8")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)


def is_platform_enabled(config: dict[str, Any], platform: str) -> bool:
    platform_config = config["platforms"].get(platform, {})
    return bool(platform_config.get("enabled"))


def has_platform_credentials(config: dict[str, Any], platform: str) -> bool:
    platform_config = config["platforms"].get(platform, {})
    credential_map = {
        "discord": [platform_config.get("webhook_url_env", "DISCORD_WEBHOOK_URL")],
        "discord_review_notify": [
            platform_config.get("webhook_url_env", "DISCORD_WEBHOOK_URL")
        ],
        "reddit": [
            platform_config.get("client_id_env", "REDDIT_CLIENT_ID"),
            platform_config.get("client_secret_env", "REDDIT_CLIENT_SECRET"),
            platform_config.get("username_env", "REDDIT_USERNAME"),
            platform_config.get("password_env", "REDDIT_PASSWORD"),
        ],
        "x": [
            platform_config.get("api_key_env", "X_API_KEY"),
            platform_config.get("api_secret_env", "X_API_SECRET"),
            platform_config.get("access_token_env", "X_ACCESS_TOKEN"),
            platform_config.get("access_token_secret_env", "X_ACCESS_TOKEN_SECRET"),
        ],
        "blog": [platform_config.get("token_env", "BLOG_API_TOKEN")],
    }

    env_names = credential_map.get(platform, [])
    if not env_names:
        return False

    return all(get_optional_env_value(name) for name in env_names)


def get_auto_publish_platforms(config: dict[str, Any]) -> list[str]:
    workflow = config.get("workflow", {})
    if not workflow.get("auto_publish", False):
        return []

    configured = workflow.get("auto_publish_platforms", ["discord", "reddit"])
    return [
        platform
        for platform in configured
        if is_platform_enabled(config, platform) and has_platform_credentials(config, platform)
    ]
