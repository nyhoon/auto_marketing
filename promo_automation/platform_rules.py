"""플랫폼별 운영 규칙 상수. 플랫폼_운영_상세_가이드.md와 동기화."""

from __future__ import annotations

from dataclasses import dataclass

FORBIDDEN_PHRASES = (
    "무료 다운로드!!!",
    "지금 바로 다운로드하세요",
    "100% 무료",
    "click here now",
    "free download now",
    "limited time only",
    "buy reviews",
    "fake reviews",
)

REDDIT_SUBREDDIT_RULES: dict[str, dict[str, str | bool]] = {
    "androiddev": {
        "self_promo": "limited",
        "link_allowed": False,
        "tone": "technical_dev_story",
        "note": "기술 개발기 중심, 링크는 댓글 요청 시만",
    },
    "IndieDev": {
        "self_promo": "allowed_with_story",
        "link_allowed": True,
        "tone": "feedback_request",
        "note": "개발 여정 + 피드백 요청",
    },
    "SideProject": {
        "self_promo": "check_rules_first",
        "link_allowed": True,
        "tone": "project_showcase",
        "note": "서브레딧 규칙 반드시 확인",
    },
    "playmygame": {
        "self_promo": "allowed",
        "link_allowed": True,
        "tone": "game_promo",
        "note": "게임 전용, 포맷 규칙 엄격",
    },
    "alphaandbetausers": {
        "self_promo": "beta_only",
        "link_allowed": True,
        "tone": "beta_recruitment",
        "note": "베타/테스트 모집만",
    },
}

X_POSTING_SCHEDULE_KST = ("08:00", "12:30", "20:30")
X_MAX_HASHTAGS = 2
X_MIN_POST_INTERVAL_HOURS = 3
X_MAX_VIDEO_SECONDS = 45

THREADS_OPTIMAL_LENGTH = (150, 300)
THREADS_MAX_POSTS_PER_DAY = 3

YOUTUBE_SHORTS_LENGTH = (15, 30)
YOUTUBE_SHORTS_HOOK_SECONDS = 3

TIKTOK_OPTIMAL_LENGTH = (15, 20)
TIKTOK_MAX_HASHTAGS = 5
TIKTOK_MAX_POSTS_PER_DAY = 3

DISCORD_NOTICE_RATIO_MAX = 0.2

GOOGLE_PLAY_TITLE_MAX = 30
GOOGLE_PLAY_SHORT_DESC_MAX = 80
GOOGLE_PLAY_KEYWORD_COUNT = (5, 8)


@dataclass(frozen=True)
class PlatformRateLimit:
    max_posts_per_day: int
    min_interval_hours: float = 0.0


PLATFORM_RATE_LIMITS: dict[str, PlatformRateLimit] = {
    "reddit": PlatformRateLimit(max_posts_per_day=1, min_interval_hours=24.0),
    "x": PlatformRateLimit(max_posts_per_day=3, min_interval_hours=3.0),
    "threads": PlatformRateLimit(max_posts_per_day=3, min_interval_hours=4.0),
    "discord": PlatformRateLimit(max_posts_per_day=5, min_interval_hours=1.0),
    "blog": PlatformRateLimit(max_posts_per_day=1, min_interval_hours=24.0),
    "youtube_shorts": PlatformRateLimit(max_posts_per_day=1, min_interval_hours=24.0),
    "tiktok": PlatformRateLimit(max_posts_per_day=1, min_interval_hours=24.0),
}

PLATFORM_PROMPT_RULES: dict[str, str] = {
    "google_play": (
        "Google Play ASO 규칙: 키워드 스터핑 금지, 허위 주장 금지, "
        "변경사항은 '문제→해결' 구조, 500자 내외."
    ),
    "reddit": (
        "Reddit 규칙: 개발기/피드백 요청 톤, 광고성 문구 금지, "
        "링크는 본문 하단에 1회만, 영어, 서브레딧 규칙 준수."
    ),
    "x": (
        "X 규칙: 280자 이내, 해시태그 1~2개(본문 끝), "
        "같은 문구 반복 금지, 링크는 포함하지 않거나 마지막에만."
    ),
    "threads": (
        "Threads 규칙: 150~300자, 질문으로 마무리, "
        "X 글 복붙 금지(문장 구조 완전 변경), 댓글 유도."
    ),
    "youtube_shorts": (
        "YouTube Shorts 규칙: 15~30초 대본, 첫 3초 후킹, "
        "제목(숫자·결과 포함), 설명란, 저작권 프리 BGM 안내, 한국어."
    ),
    "tiktok": (
        "TikTok 규칙: 15~20초 대본, 완시청률 고려, "
        "해시태그 3~5개(니치), Shorts와 다른 편집 권장, 한국어."
    ),
    "discord": (
        "Discord 규칙: 짧은 공지 + 질문 1개, "
        "공지 톤 대신 대화 유도, 한국어."
    ),
    "blog": (
        "블로그 SEO 규칙: 문제 해결형 H1/H2 구조, "
        "키워드 자연 포함, 앱 소개는 글 후반부, 한국어."
    ),
}
