# News_Agent — VPS 이전 & 웹 서비스 설계

> GitHub Pages 정적 사이트에서 VPS 기반 웹 서비스로 전환하는 설계 문서.

---

## 배경

### 현재 구조 (GitHub Pages)

```
[GitHub Actions (매일 KST 06:00)]
   ↓
collect → brief → deploy
   ↓
[web/ 폴더] → git push → [GitHub Pages 정적 호스팅]
                          ↓
                    https://bapuri-commits.github.io/News_Agent/
                          ↓
                    [이메일 발송 (Gmail SMTP)]
```

**한계:**
- 정적 HTML만 가능 — 사용자 인터랙션 불가
- 서버 사이드 로직 없음 → 피드백, 검색, 챗봇 구현 불가
- UI 개선 범위가 프론트엔드 정적 파일로 제한
- 빌드/배포 시간이 GitHub Actions 러너에 의존

### 전환 목표

- nginx로 정적 브리핑 페이지 서빙 (기존 기능 유지)
- FastAPI 백엔드 추가로 동적 기능 활성화
- GitHub Pages 대비 높은 수준의 UI/UX 제공
- 기존 IMPROVEMENT-BACKLOG의 피드백/챗봇 기능 구현 기반 마련

---

## 새 아키텍처

```
[VPS cron (매일 UTC 21:00 = KST 06:00)]
   ↓
collect → brief → deploy → ingest
   ↓                         ↓
[/opt/data/news-agent/]    [briefings.db 인덱싱]
   ↓
[nginx :80/443]
   ├── /                → 정적 브리핑 페이지 (web/)
   ├── /api/feedback    → FastAPI 백엔드
   ├── /api/chat        → Q&A 챗봇 (RAG)
   └── /api/briefings   → 브리핑 데이터 API
```

### GitHub Actions 전환 전략

| 단계 | Actions | VPS | 비고 |
|------|---------|-----|------|
| Phase 1 | 유지 (Pages + 이메일) | nginx 정적 서빙만 | 병행 운영, 안정성 확인 |
| Phase 2 | 이메일만 유지 | 정적 + API 서빙 | VPS가 메인 |
| Phase 3 | 비활성화 | 전부 VPS | 이메일도 VPS에서 발송 |

---

## Phase 1 — 정적 서빙 이전

> DevOps 로드맵 Stage 4 (nginx)에서 진행

### 변경 사항

- nginx로 `/opt/data/news-agent/web/` 서빙
- cron으로 매일 파이프라인 실행 (GitHub Actions와 병행)
- 도메인 연결 + HTTPS (Stage 5)

### 디렉토리 구조

```
/opt/apps/news-agent/         ← git clone (코드)
   ├── src/                   ← 파이프라인 코드
   ├── output -> /opt/data/news-agent/output   (심링크)
   ├── web -> /opt/data/news-agent/web         (심링크)
   └── .env -> /opt/envs/news-agent.env        (심링크)

/opt/data/news-agent/         ← 런타임 데이터
   ├── output/                ← 수집/브리핑 결과
   │   ├── collected/
   │   ├── briefings/
   │   └── ...
   └── web/                   ← nginx 서빙 대상
       ├── index.html
       ├── 2026-03-05.html
       └── ...
```

### nginx 설정 (예시)

```nginx
server {
    listen 80;
    server_name news.도메인;

    root /opt/data/news-agent/web;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
```

### 현재 상태 (2026-03-05 완료)

- [x] VPS에 코드 배포 (`/opt/apps/news-agent/`)
- [x] 심링크 구조 (output, web, .env)
- [x] collect → brief → deploy 수동 실행 성공
- [ ] nginx 설치 및 설정 (Stage 4)
- [ ] cron 자동화 (Stage 7)
- [ ] 도메인 + HTTPS (Stage 5)

---

## Phase 2 — FastAPI 백엔드 추가

> IMPROVEMENT-BACKLOG #2 (피드백) + #3 (Q&A 챗봇) 구현

### 백엔드 구조

```
/opt/apps/news-agent/
   └── backend/               ← 신규
       ├── main.py            ← FastAPI 앱
       ├── models.py          ← DB 모델
       ├── db.py              ← SQLite + FTS5
       ├── routers/
       │   ├── feedback.py    ← POST /api/feedback
       │   ├── chat.py        ← POST /api/chat
       │   └── briefings.py   ← GET /api/briefings
       └── requirements.txt
```

### API 엔드포인트

| Method | Path | 설명 |
|--------|------|------|
| POST | `/api/feedback` | 기사 👍/👎 피드백 저장 |
| POST | `/api/chat` | 기사 기반 Q&A (RAG) |
| GET | `/api/briefings` | 브리핑 목록/검색 |
| POST | `/api/briefings/ingest` | 당일 브리핑 DB 인덱싱 |

### 데이터 저장

```
/opt/data/news-agent/
   └── db/                    ← 신규
       ├── feedback.db        ← 피드백 누적
       └── briefings.db       ← FTS5 인덱싱
```

### nginx 설정 (Phase 2)

```nginx
server {
    server_name news.도메인;

    # 정적 브리핑 페이지
    location / {
        root /opt/data/news-agent/web;
        try_files $uri $uri/ =404;
    }

    # API 프록시
    location /api/ {
        proxy_pass http://127.0.0.1:8100;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 실행 방식

- FastAPI: systemd 서비스로 상시 실행 (uvicorn, 포트 8100)
- 파이프라인: cron (기존과 동일, ingest 단계 추가)

---

## Phase 3 — UI 강화

> GitHub Pages에서 불가능했던 기능들

### 가능해지는 것

| 기능 | GitHub Pages | VPS |
|------|:----------:|:---:|
| 정적 브리핑 페이지 | O | O |
| 피드백 (👍/👎) | X | O |
| Q&A 챗봇 | X | O |
| 실시간 검색 | X (JS 필터링만) | O (서버 사이드 FTS) |
| 사용자 인증 | X | O (선택) |
| SSR / 동적 페이지 | X | O |

### UI 개선 방향

**현재 (정적 HTML)**:
- deployer가 생성하는 고정된 HTML 카드
- 테마는 Python 코드에서 빌드 시 결정
- 인터랙션: 날짜 검색(JS 필터링), 탭 전환 정도

**Phase 3 목표**:
- 브리핑 카드 + 피드백 버튼 (👍/👎)
- 플로팅 챗 UI (기사 기반 Q&A)
- 카테고리별 "더 보기/줄이기" 토글
- 기사 키워드 하이라이트
- 히스토리 타임라인 (주간/월간 트렌드 시각화)
- 다크모드 토글

### 프론트엔드 전략 결정 (미정)

| 옵션 | 장점 | 단점 |
|------|------|------|
| **현재 구조 유지** (Python 빌드 HTML + Vanilla JS) | 단순, 추가 빌드 불필요 | 복잡한 UI 한계 |
| **경량 프레임워크** (Alpine.js / htmx) | 기존 HTML에 최소 변경으로 인터랙션 추가 | 복잡한 상태관리 어려움 |
| **SPA** (React / Svelte) | 풍부한 UI, 컴포넌트 재사용 | 빌드 파이프라인 추가, 과할 수 있음 |

**권장**: Phase 2까지는 현재 구조 + Vanilla JS(fetch)로 충분. Phase 3에서 UI 복잡도가 올라가면 Alpine.js 또는 htmx 도입 검토.

---

## 파이프라인 변경 요약

### 현재

```bash
collect → brief → deploy → (git push) → (GitHub Pages)
```

### Phase 2 이후

```bash
collect → brief → deploy → ingest
                    ↓          ↓
              web/ 갱신    briefings.db 인덱싱
```

### cron 예시 (UTC)

```bash
# 매일 KST 06:00 = UTC 21:00
0 21 * * * /opt/apps/news-agent/scripts/daily-pipeline.sh >> /opt/logs/news-agent/daily.log 2>&1
```

### daily-pipeline.sh (예시)

```bash
#!/bin/bash
set -e
cd /opt/apps/news-agent
source .venv/bin/activate
DATE=$(date -u +%Y-%m-%d)

python -m src.main collect --date "$DATE"
python -m src.main brief --date "$DATE"
python -m src.main deploy

# Phase 2: DB 인덱싱
# curl -X POST http://127.0.0.1:8100/api/briefings/ingest -d "{\"date\": \"$DATE\"}"
```

---

## 비용 예상

| 항목 | 월 비용 |
|------|--------|
| Anthropic API (daily brief) | ~$15~25 |
| Anthropic API (Q&A Haiku, 월 100회) | ~$0.50 |
| VPS (Contabo, 이미 보유) | $0 (추가 비용 없음) |
| 도메인 (.xyz 등) | ~$0.25/월 ($3/년) |

---

## 관련 문서

- `docs/DEPLOYMENT.md` — VPS 배포 절차
- `docs/IMPROVEMENT-BACKLOG.md` — 기능 백로그 (#2 피드백, #3 챗봇)
- The Record `devops-learning-roadmap.md` — DevOps 학습 Stage와 연계
