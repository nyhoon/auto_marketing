"""발행 전 compliance 검증. 플랫폼_운영_상세_가이드.md 규칙을 코드로 강제."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

from common import BASE_DIR
from platform_rules import FORBIDDEN_PHRASES, PLATFORM_RATE_LIMITS, REDDIT_SUBREDDIT_RULES

PUBLISH_LOG_PATH = BASE_DIR.parent / "generated" / ".publish_log.json"


@dataclass(frozen=True)
class ComplianceResult:
    passed: bool
    violations: tuple[str, ...]


def check_content(platform: str, content: str) -> ComplianceResult:
    violations: list[str] = []

    for phrase in FORBIDDEN_PHRASES:
        if phrase.lower() in content.lower():
            violations.append(f"금지 문구 포함: '{phrase}'")

    if platform == "x" and len(content) > 280:
        violations.append(f"X 글자 수 초과: {len(content)}/280")

    if platform == "reddit":
        link_count = content.lower().count("http")
        if link_count > 1:
            violations.append(f"Reddit 링크 과다: {link_count}개 (최대 1개)")

    if platform == "threads":
        if len(content) > 500:
            violations.append(f"Threads 글자 수 과다: {len(content)}/500")

    return ComplianceResult(passed=len(violations) == 0, violations=tuple(violations))


def check_duplicate_across_platforms(
    current_platform: str,
    content: str,
    all_contents: dict[str, str],
    similarity_threshold: float = 0.7,
) -> ComplianceResult:
    violations: list[str] = []
    current_normalized = _normalize(content)

    for platform, other_content in all_contents.items():
        if platform == current_platform:
            continue
        other_normalized = _normalize(other_content)
        if not other_normalized or not current_normalized:
            continue

        similarity = _jaccard_similarity(current_normalized, other_normalized)
        if similarity >= similarity_threshold:
            violations.append(
                f"{current_platform} ↔ {platform} 유사도 {similarity:.0%} "
                f"(임계값 {similarity_threshold:.0%}) — 복붙 의심"
            )

    return ComplianceResult(passed=len(violations) == 0, violations=tuple(violations))


def check_rate_limit(platform: str, config: dict) -> ComplianceResult:
    violations: list[str] = []
    rate_limit = PLATFORM_RATE_LIMITS.get(platform)
    if rate_limit is None:
        return ComplianceResult(passed=True, violations=())

    platform_config = config.get("platforms", {}).get(platform, {})
    max_per_day = platform_config.get("max_posts_per_day", rate_limit.max_posts_per_day)

    log = _load_publish_log()
    today = datetime.now().strftime("%Y-%m-%d")
    today_count = sum(
        1 for entry in log
        if entry.get("platform") == platform and entry.get("date") == today
    )

    if today_count >= max_per_day:
        violations.append(
            f"{platform} 일일 게시 한도 초과: {today_count}/{max_per_day}"
        )

    if rate_limit.min_interval_hours > 0:
        last_entry = _get_last_publish(log, platform)
        if last_entry:
            last_time = datetime.fromisoformat(last_entry["timestamp"])
            min_next = last_time + timedelta(hours=rate_limit.min_interval_hours)
            if datetime.now() < min_next:
                violations.append(
                    f"{platform} 게시 간격 미달: "
                    f"다음 가능 시각 {min_next.strftime('%H:%M')}"
                )

    return ComplianceResult(passed=len(violations) == 0, violations=tuple(violations))


def check_reddit_subreddit(subreddit: str) -> ComplianceResult:
    violations: list[str] = []
    rule = REDDIT_SUBREDDIT_RULES.get(subreddit)

    if rule is None:
        violations.append(
            f"r/{subreddit} 규칙이 config에 미등록 — "
            f"platform_rules.py 또는 config에 추가 후 게시"
        )
    elif rule.get("self_promo") == "check_rules_first":
        violations.append(
            f"r/{subreddit}: 서브레딧 규칙 수동 확인 필요 (self_promo=check_rules_first)"
        )

    return ComplianceResult(passed=len(violations) == 0, violations=tuple(violations))


def check_reddit_warmup(config: dict) -> ComplianceResult:
    violations: list[str] = []
    reddit_config = config.get("platforms", {}).get("reddit", {})
    min_age_days = reddit_config.get("min_account_age_days", 14)
    account_created = reddit_config.get("account_created_date", "")

    if account_created:
        created = datetime.strptime(account_created, "%Y-%m-%d")
        age_days = (datetime.now() - created).days
        if age_days < min_age_days:
            violations.append(
                f"Reddit 계정 워밍업 미완: {age_days}일 "
                f"(최소 {min_age_days}일 필요)"
            )

    return ComplianceResult(passed=len(violations) == 0, violations=tuple(violations))


def run_all_checks(
    platform: str,
    content: str,
    all_contents: dict[str, str],
    config: dict,
) -> ComplianceResult:
    checks = [
        check_content(platform, content),
        check_duplicate_across_platforms(platform, content, all_contents),
        check_rate_limit(platform, config),
    ]

    if platform == "reddit":
        subreddits = config.get("platforms", {}).get("reddit", {}).get("subreddits", [])
        for sub in subreddits:
            checks.append(check_reddit_subreddit(sub))
        checks.append(check_reddit_warmup(config))

    all_violations: list[str] = []
    for result in checks:
        all_violations.extend(result.violations)

    return ComplianceResult(passed=len(all_violations) == 0, violations=tuple(all_violations))


def record_publish(platform: str, external_id: str = "") -> None:
    log = _load_publish_log()
    log.append({
        "platform": platform,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "external_id": external_id,
    })
    _save_publish_log(log)


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


def _jaccard_similarity(a: str, b: str) -> float:
    set_a = set(a.split())
    set_b = set(b.split())
    if not set_a or not set_b:
        return 0.0
    intersection = set_a & set_b
    union = set_a | set_b
    return len(intersection) / len(union)


def _load_publish_log() -> list[dict]:
    if not PUBLISH_LOG_PATH.exists():
        return []
    return json.loads(PUBLISH_LOG_PATH.read_text(encoding="utf-8"))


def _save_publish_log(log: list[dict]) -> None:
    PUBLISH_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    PUBLISH_LOG_PATH.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_last_publish(log: list[dict], platform: str) -> dict | None:
    platform_entries = [e for e in log if e.get("platform") == platform]
    if not platform_entries:
        return None
    return platform_entries[-1]
