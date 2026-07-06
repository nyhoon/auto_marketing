import json
from typing import Any

import requests

from common import get_optional_env_value, is_platform_enabled, load_config


def notify_n8n(output_dir, release, platform_list: list[str], config: dict[str, Any]) -> bool:
    n8n_config = config.get("n8n", {})
    if not n8n_config.get("enabled"):
        return False

    webhook_env = n8n_config.get("webhook_url_env", "N8N_WEBHOOK_URL")
    webhook_url = get_optional_env_value(webhook_env)
    if not webhook_url:
        print(f"[WARN] n8n 활성화됐지만 {webhook_env} 미설정 — 건너뜀")
        return False

    payload = {
        "event": "promo_drafts_ready",
        "release_title": release.title,
        "release_tag": release.tag,
        "output_dir": str(output_dir),
        "platforms": platform_list,
        "review_command": "python promo_automation/run_pipeline.py --publish --approve",
    }

    response = requests.post(webhook_url, json=payload, timeout=30)
    if response.status_code >= 400:
        print(f"[FAIL] n8n webhook: {response.status_code} {response.text}")
        return False

    print("[OK] n8n webhook 전송 완료")
    return True
