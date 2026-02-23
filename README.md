# News Agent — 뉴스 브리핑 에이전트

매일 아침, 반도체 Fab · 데이터센터 · 건설/수주 · 투자/정책 분야의 핵심 뉴스를
자동 수집 → 클러스터링 → 요약하여 **5~20분 브리핑**으로 제공하는 시스템.

> 배포 사이트: <https://bapuri-commits.github.io/News_Agent/>

## 핵심 특징

- **2트랙 출력**: 모바일 친화 카드 브리프(HTML) + 출처 링크 포함 레퍼런스 문서(HTML, 전체 복사 지원)
- **22개 카테고리**: INITIAL-SCOPE 16개 서브스코프 완전 반영 (반도체 4 + DC 3 + 건설 5 + 투자 4 + 테마 5 + 전용 1)
- **편향 억제**: Stable Profile 기반 필터링, 소스 다양성 강제 (전문매체 최소 보장), S7 내부 보도자료 중복 제거, Fact/Inference 분리
- **SK에코플랜트 관전 오버레이**: 수주믹스, 재무/차입, PF 우발, IPO 시그널 매일 체크
- **자동화**: GitHub Actions 매일 KST 06:00 자동 실행 + 이메일 발송
- **품질 자동 검증**: Design Lint (Fact 길이, 출처 누락, 빈 카테고리, 소스 편향 경고)
- **인덱스 날짜 검색**: 달력 팝업으로 특정 날짜 브리핑 필터링
- **가족 전용**: GitHub Pages 배포, 멀티테넌트/공개 SaaS 고려 없음

## 아키텍처

7단계 파이프라인으로 구성된 3개 프로그램:

```
Program #1 — Profile 추출 (1회성)
  Phase 1: ChatGPT Export ZIP 파싱 → 대화 추출
  Phase 2: PII 마스킹 + Chunking
  Phase 3: LLM Micro-summary 생성 (Claude)
  Phase 4: Stable Profile 빌드 (26개 우선순위)

Program #2 — 뉴스 파이프라인 (매일 자동)
  Phase 5: Google News RSS + 14개 전문매체 RSS 수집 → 2단계 중복 제거 → 전문매체 보너스 스코어링 → 관련성 필터링
  Phase 6: 4단계 LLM 브리핑 생성
    → Stage 1: 클러스터링 + Top 5 선정 (Haiku)
    → Stage 2: Top 5 심층 분석 (Opus)
    → Stage 3: 카테고리별 요약 (Sonnet)
    → Stage 4: SK에코플랜트 Lens (Sonnet)

Program #3 — 배포 (매일 자동)
  Phase 7: 정적 사이트 빌드 → GitHub Pages 배포 + 이메일 발송
```

## Tech Stack

| 영역 | 기술 |
|------|------|
| 언어 | Python 3.12+ |
| LLM | Anthropic Claude 4 API (Haiku 4.5, Sonnet 4, Opus 4) |
| 뉴스 수집 | Feedparser, BeautifulSoup4, googlenewsdecoder |
| 기사 크롤링 | Playwright (Chromium) |
| 자동화 | GitHub Actions (cron + workflow_dispatch) |
| 배포 | GitHub Pages (정적 사이트) |
| 알림 | Gmail SMTP (action-send-mail) |

## Getting Started

### 사전 요구 사항

- Python 3.12+
- Anthropic API 키

### 설치

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS/Linux

pip install -r requirements.txt
playwright install chromium
```

### 환경 변수

프로젝트 루트에 `.env` 파일 생성:

```
ANTHROPIC_API_KEY=sk-ant-...
```

GitHub Actions 자동화를 위한 추가 Secrets (GitHub 리포지토리 설정):

- `ANTHROPIC_API_KEY` — Anthropic API 키
- `EMAIL_USERNAME` — Gmail 발신 주소
- `EMAIL_PASSWORD` — Gmail 앱 비밀번호
- `EMAIL_TO` — 수신 이메일 주소

### CLI 사용법

```bash
# Program #1: Profile 추출 (1회성)
python -m src.main parse --zip path/to/chatgpt-export.zip   # Phase 1
python -m src.main preprocess                                # Phase 2
python -m src.main summarize                                 # Phase 3
python -m src.main build-profile                             # Phase 4

# Program #2: 뉴스 파이프라인 (매일)
python -m src.main collect --date 2026-02-23                 # Phase 5
python -m src.main brief --date 2026-02-23                   # Phase 6

# Program #3: 배포
python -m src.main deploy                                    # Phase 7
python -m src.main deploy --push                             # Phase 7 + git push
```

## Project Structure

```
News_Agent/
├── .github/workflows/
│   ├── daily-briefing.yml          # 매일 KST 06:00 자동 실행 워크플로우
│   └── deploy-pages.yml            # GitHub Pages 수동 배포
│
├── docs/                           # 설계 문서 및 핸드오프 기록
│   ├── initial_design/             # 초기 설계 문서
│   ├── HANDOFF-*.md                # 단계별 핸드오프 문서 (phase2~9, design-polish 등)
│   ├── PHASE3-REPORT.md            # Phase 3 결과 리포트
│   ├── father-profile-form.md      # 프로필 설문 양식
│   ├── father-profile-raw.md       # 프로필 원시 데이터
│   ├── open-questions-review.md    # 미결 이슈 검토
│   └── IMPROVEMENT-BACKLOG.md      # 향후 개선 백로그
│
├── src/                            # 메인 소스 코드
│   ├── main.py                     # CLI 진입점 (7단계 파이프라인)
│   ├── config.py                   # 경로 및 상수 설정
│   │
│   ├── models/                     # 데이터 모델
│   │   ├── article.py              #   Article 모델
│   │   ├── conversation.py         #   Conversation / Message 모델
│   │   └── summary.py              #   Summary 모델
│   │
│   ├── parser/                     # Phase 1: ChatGPT Export 파싱
│   │   ├── zip_explorer.py         #   ZIP 파일 추출
│   │   └── conversation_parser.py  #   대화 JSON 파싱
│   │
│   ├── preprocess/                 # Phase 2: 전처리
│   │   ├── pii_masker.py           #   개인정보 마스킹
│   │   └── chunker.py              #   텍스트 청킹
│   │
│   ├── summarizer/                 # Phase 3: LLM 요약
│   │   ├── base.py                 #   요약기 인터페이스
│   │   └── llm_summarizer.py       #   Claude 기반 요약기
│   │
│   ├── profiler/                   # Phase 4: 프로필 빌드
│   │   ├── survey_loader.py        #   설문 데이터 로더
│   │   └── profile_builder.py      #   Stable Profile 빌더
│   │
│   ├── collector/                  # Phase 5: 뉴스 수집
│   │   ├── gnews_client.py         #   Google News RSS 클라이언트
│   │   ├── rss_client.py           #   전문매체 RSS 클라이언트
│   │   ├── news_api_client.py      #   NewsAPI 클라이언트 (선택적)
│   │   ├── query_builder.py        #   프로필 기반 검색 쿼리 생성
│   │   ├── dedup.py                #   기사 중복 제거
│   │   └── article_filter.py       #   관련성 필터링
│   │
│   ├── briefer/                    # Phase 6: 브리핑 생성
│   │   ├── briefing_generator.py   #   4단계 LLM 파이프라인
│   │   ├── article_crawler.py      #   기사 본문 크롤러
│   │   ├── prompts.py              #   LLM 프롬프트
│   │   ├── markdown_renderer.py    #   레퍼런스 문서 렌더러 (출처 링크 포함 MD)
│   │   ├── html_renderer.py        #   카드 브리프 HTML 렌더러
│   │   ├── design_system.py        #   디자인 시스템 상수
│   │   ├── themes.py               #   테마 정의
│   │   └── constants.py            #   브리핑 상수
│   │
│   ├── deployer/                   # Phase 7: 배포
│   │   ├── site_builder.py         #   정적 사이트 빌더
│   │   ├── index_generator.py      #   인덱스 페이지 생성
│   │   ├── nav_injector.py         #   네비게이션 주입
│   │   └── text_page_generator.py  #   레퍼런스 HTML 페이지 생성 (출처 링크 + 전체 복사)
│   │
│   └── data/                       # 정적 데이터
│       ├── keywords.json           #   산업 키워드 및 엔티티
│       └── rss_feeds.json          #   14개 RSS 피드 설정
│
├── tests/                          # 테스트
│   ├── test_collector.py
│   ├── test_deployer.py
│   ├── test_parser.py
│   ├── test_preprocess.py
│   ├── test_profiler.py
│   └── fixtures/
│       └── sample_conversations.json
│
├── output/                         # 생성 산출물 (gitignored)
│   ├── stable_profile.json         #   Stable Profile (커밋됨)
│   ├── collected/                  #   일자별 수집 기사
│   ├── briefings/                  #   일자별 브리핑 (JSON, MD, HTML)
│   └── micro_summaries/            #   LLM 마이크로 요약
│
├── web/                            # 배포용 정적 사이트 (GitHub Pages)
│   ├── index.html
│   ├── YYYY-MM-DD.html             #   일자별 카드 브리프
│   └── YYYY-MM-DD-text.html        #   일자별 레퍼런스 페이지
│
├── .env                            # API 키 (gitignored)
├── .gitignore
└── requirements.txt
```

## 데이터 흐름

```
ChatGPT Export ZIP
  → 대화 파싱 → PII 마스킹 → 청킹
  → LLM Micro-summary → Stable Profile (26개 우선순위)
      ↓
매일 자동 실행 (GitHub Actions, KST 06:00)
      ↓
Google News RSS + 14개 전문매체 RSS
  → 중복 제거 → 프로필 기반 관련성 필터링 (최대 50건)
  → 4단계 LLM 브리핑 생성
  → 카드 브리프(HTML) + 레퍼런스 페이지(HTML) 렌더링
  → GitHub Pages 배포 + 이메일 발송
```

## 테스트

```bash
pytest tests/    # 112개 테스트
```

## License

Private — 가족 내부 전용
