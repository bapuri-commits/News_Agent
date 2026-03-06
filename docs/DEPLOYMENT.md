# News_Agent — VPS 배포 가이드

> ⚠️ **초안 문서** — 각 Stage 진행 시 실제 환경에 맞게 수정될 수 있음.

> Contabo VPS에서 cron으로 매일 뉴스 브리핑을 생성하고, nginx로 정적 페이지를 서빙하는 절차.
> DevOps 학습 로드맵 Stage 2, 4, 6, 7에서 사용.

---

## 아키텍처 개요

```
[cron (매일 KST 06:00)]
   ↓
[collect → brief → deploy]
   ↓
[output/briefings/]  →  [web/]  →  [nginx 정적 서빙]
```

기존 GitHub Actions 파이프라인과 병행 또는 전환 가능.

---

## 사전 요구사항

- Python 3.12+
- Playwright + Chromium (headless)
- nginx (정적 서빙용, Stage 5 이후)

---

## 환경변수

| 변수 | 필수 | 설명 |
|------|------|------|
| `ANTHROPIC_API_KEY` | ✅ | Claude API (브리핑 생성) |

Gmail 발송은 GitHub Actions에서만 사용 (VPS에서는 선택):

| 변수 | 설명 |
|------|------|
| `EMAIL_USERNAME` | Gmail 발신 주소 |
| `EMAIL_PASSWORD` | Gmail 앱 비밀번호 |
| `EMAIL_TO` | 수신 메일 주소 |

---

## Stage 2 — 수동 배포 (첫 번째 배포 연습)

```bash
# 1. 레포 클론
cd /opt
git clone https://github.com/사용자/News_Agent.git
cd News_Agent

# 2. Python 가상환경
python3.12 -m venv .venv
source .venv/bin/activate

# 3. 의존성 설치
pip install -r requirements.txt
playwright install chromium --with-deps

# 4. 환경변수
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 5. 수동 실행
python -m src.main collect --date 2026-03-05
python -m src.main brief --date 2026-03-05
python -m src.main deploy
```

---

## Stage 4 — nginx 정적 서빙

### /etc/nginx/sites-available/news-agent

```nginx
# TODO: Stage 5에서 작성
# server {
#     listen 80;
#     server_name news.도메인;
#
#     root /opt/News_Agent/web;
#     index index.html;
#
#     location / {
#         try_files $uri $uri/ =404;
#     }
# }
```

---

## Stage 7 — cron 자동화

```bash
# TODO: Stage 8에서 등록
# crontab -e
# 0 21 * * * cd /opt/News_Agent && /opt/News_Agent/.venv/bin/python -m src.main collect --date $(date +\%Y-\%m-\%d) && /opt/News_Agent/.venv/bin/python -m src.main brief --date $(date +\%Y-\%m-\%d) && /opt/News_Agent/.venv/bin/python -m src.main deploy >> /var/log/news-agent.log 2>&1
```

주의사항:
- cron 환경에서는 `.venv` 내 Python 절대 경로 사용
- cron의 PATH에 Playwright/Chromium 경로 포함 필요
- stdout/stderr를 로그 파일로 리다이렉트

---

## GitHub Actions와의 관계

현재 `daily-briefing.yml`이 GitHub Actions에서 매일 실행 중.

옵션:
1. **병행**: Actions는 GitHub Pages 배포 + 이메일용, VPS cron은 로컬 사본 유지
2. **VPS 전환**: Actions를 비활성화하고 VPS에서 전부 처리
3. **Actions → VPS 트리거**: Actions에서 SSH로 VPS 실행만 트리거

---

## 알려진 이슈

- Playwright가 VPS headless 환경에서 의존성 추가 설치 필요 (`--with-deps`)
- Google News URL 디코딩 시 Playwright fallback 사용 → 메모리 순간 급증 가능
- `output/` 폴더 누적 시 디스크 관리 필요 (오래된 브리핑 정리 정책)
