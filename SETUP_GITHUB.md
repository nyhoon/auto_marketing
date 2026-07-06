# GitHub 연결 가이드

Repo: https://github.com/nyhoon/auto_marketing

## 1. GitHub Secrets 등록 (필수)

**Settings → Secrets and variables → Actions → New repository secret**

| Secret 이름 | 상태 | 설명 |
|-------------|------|------|
| `OPENAI_API_KEY` | **필수** | OpenAI API 키 (채팅에 노출됐으면 재발급 권장) |

### 나중에 추가 (자동 발행용)

| Secret | 용도 |
|--------|------|
| `DISCORD_WEBHOOK_URL` | 검토 알림 + 공지 |
| `X_API_KEY` / `X_API_SECRET` / `X_ACCESS_TOKEN` / `X_ACCESS_TOKEN_SECRET` | X 자동 게시 |
| `REDDIT_CLIENT_ID` / `REDDIT_CLIENT_SECRET` / `REDDIT_USERNAME` / `REDDIT_PASSWORD` | Reddit |
| `BLOG_API_TOKEN` | WordPress |
| `N8N_WEBHOOK_URL` | n8n 연동 |

## 2. Actions 실행 방법

1. https://github.com/nyhoon/auto_marketing/actions
2. **App Promo Automation** 선택
3. **Run workflow** 클릭
4. 입력:
   - `release_title`: `NeoFall v1.0`
   - `release_body`: 업데이트 내용
5. 완료 후 **Artifacts**에서 `promo-posts` 다운로드

## 3. 로컬 실행

```bash
cd promo_automation
pip install -r requirements.txt
copy config.example.json config.json
# .env 에 OPENAI_API_KEY 설정됨

python export_variations.py
python run_pipeline.py --all --use-variations
```

## 4. NeoFall 릴리스 연동

NeoFall 업데이트 시 Actions에서 수동 실행하고 `release_body`에 변경사항을 붙여넣으세요.
