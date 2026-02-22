# Phase 5~6 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 7 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Program #1(Phase 1~4)로 Stable Profile 추출 완료. Program #2(Phase 5~6)로 뉴스 수집 + 브리핑 생성까지 완료. Phase 7부터 웹 배포.

---

## 전체 파이프라인 완성 상태

```
Program #1: 프로필 추출 ━━━━━━━━━━━━━━━ 완료
  Phase 1: ZIP 파싱 (65개 대화, 643개 메시지)         ✅
  Phase 2: PII 마스킹 + 청킹 (73개 chunk)             ✅
  Phase 3: Claude Opus micro-summary (28개 비즈니스)   ✅
  Phase 4: Stable Profile 확정 (26개 우선순위)          ✅

Program #2: 뉴스 파이프라인 ━━━━━━━━━━━━━ 완료
  Phase 5: News Collector (GNews + RSS 12개 피드)      ✅
  Phase 6: Briefing Generator (4단계 LLM 파이프라인)   ✅
  Phase 7: 웹 배포 (정적 사이트 + GitHub Pages)        ⬜ ← 다음
```

---

## Phase 5: News Collector — 완료

### 아키텍처 변경: NewsAPI → Google News RSS

원래 설계는 NewsAPI(유료) + RSS 하이브리드였으나, MVP 비용 문제로 **Google News RSS 키워드 검색**으로 완전 대체. 무료, API 키 불필요, 한/영 양방향 검색.

### 수집 흐름

```
stable_profile.json
  ├─ query_builder.py → 17개 검색 쿼리 생성
  │   (일반 10 + SK에코 4 + trigger 3)
  │
  ├─ [경로 A] GNews RSS 검색 (when:2d 날짜 필터)
  │   └─ 한/영 양방향 × 17쿼리 → ~568건
  │
  ├─ [경로 B] RSS 피드 구독 (12개 전문매체)
  │   └─ DCD, EE Times, SemiEng, Bloomberg, CNBC,
  │      TechCrunch, 전자신문, 더일렉, 한경, 매경, 뉴시스, 아이뉴스24
  │      → ~438건
  │
  └─ 병합 → dedup (Jaccard 제목 유사도) → filter (프로필 기반 스코어링)
      └─ collected/YYYY-MM-DD.json (30~50건)
```

### 스코어링 규칙

- top_priorities score 3 키워드 매치: +0.3
- SK에코플랜트 직접 언급: +0.5
- must_include_triggers 매치: +0.5
- avoid 항목: -0.5
- **freshness**: 1일 이내 +0.15, 3일 초과 -0.4
- 소스 다양성: soft cap 40%, hard cap 60%
- **전문매체 최소 보장**: S1/S2/S5 각 최소 1건 (score >= 0)

### 구현 파일

| 파일 | 역할 |
|------|------|
| `src/collector/gnews_client.py` | Google News RSS 키워드 검색 (NewsAPI 대체) |
| `src/collector/rss_client.py` | RSS 피드 구독 + 파싱 |
| `src/collector/query_builder.py` | 프로필 → 17개 검색 쿼리 |
| `src/collector/article_filter.py` | 스코어링 + 필터링 + 소스 리밸런싱 |
| `src/collector/dedup.py` | URL + Jaccard 제목 유사도 중복 제거 |
| `src/collector/news_api_client.py` | (비활성 — 유료 전환 시 재활용 가능) |
| `src/models/article.py` | Article 데이터 모델 |
| `src/data/rss_feeds.json` | RSS 피드 12개 목록 |

---

## Phase 6: Briefing Generator — 완료

### 4단계 LLM 파이프라인 (모델 믹스)

```
collected/YYYY-MM-DD.json (30~50건)
    ↓
[Stage 1] Sonnet — 클러스터링 + Top 5 선정 (~8초)
    ↓
[크롤링] Top 5 + SK에코 기사 본문 추출 시도
    ↓
[Stage 2] Opus — Top 5 심층 Fact/Impact/Risk/Next (~2분)
    ↓
[Stage 3] Sonnet — 카테고리별 요약 (~22초)
    ↓
[Stage 4] Opus — SK에코플랜트 4대 렌즈 분석 (~12초)
    ↓
output/briefings/YYYY-MM-DD.json  (구조화된 브리핑)
output/briefings/YYYY-MM-DD.md   (텍스트 브리핑)
output/briefings/YYYY-MM-DD.html (웹 UI 브리핑)
```

### 브리핑 섹션 구조

| 섹션 | 내용 | 소스 |
|------|------|------|
| **Top 5** | 오늘 가장 중요한 5개, Fact/Impact/Risk/Next 포함 | Stage 2 (Opus) |
| **SK에코플랜트 렌즈** | 수주·믹스, 현금흐름, PF/우발채무, IPO/경쟁사 | Stage 4 (Opus) |
| **카테고리별 동향** | fab_capex, dc_build, epc_award 등 | Stage 3 (Sonnet) |
| **리스크 종합** | Top 5에서 추출된 리스크 모음 | 자동 추출 |
| **Next Signals** | 향후 확인 사항 | 자동 추출 |
| **소스 분포** | S1~S7 비율 시각화 | 자동 계산 |

### HTML 동적 테마 (6종, 콘텐츠 기반 자동 선택)

| 테마 | 조건 |
|------|------|
| Risk Alert (빨강) | 리스크 4건 이상 |
| SK Focus (주황) | SK에코 5건+ 또는 Top5에 SK에코 |
| Tech Focus (파랑) | Fab/CapEx/패키징 지배 |
| Infra Focus (보라) | DC/전력/냉각 지배 |
| Deal Flow (초록) | EPC/M&A 지배 |
| Market Watch (틸) | PF/ESG 지배 |

> 사용자 의견: 이 동적 테마는 원래 의도한 방식이 아님. MVP 이후 재설계 예정.

### 구현 파일

| 파일 | 역할 |
|------|------|
| `src/briefer/briefing_generator.py` | 4단계 파이프라인 오케스트레이터 |
| `src/briefer/prompts.py` | 단계별 LLM 프롬프트 + 출력 스키마 |
| `src/briefer/article_crawler.py` | Top 5 기사 본문 크롤링 |
| `src/briefer/markdown_renderer.py` | JSON → Markdown 렌더러 |
| `src/briefer/html_renderer.py` | JSON → HTML 렌더러 (Opal 스타일) |
| `src/briefer/constants.py` | 공용 상수 (카테고리 라벨/색상) |

---

## 구현 감사 — 발견 및 수정 완료된 버그

| # | 문제 | 원인 | 수정 |
|---|------|------|------|
| 1 | Stage 1에서 SK에코 48/50건 과대선정 | 프롬프트 기준 느슨 | "제목에 직접 등장 + 최대 10건" 제한 |
| 2 | Google News 크롤링 100% 실패 | `requests.head`로 JS redirect 불가 | `requests.get` + HTML 파싱으로 변경 |
| 3 | Top 5에 sources/categories 누락 | Stage 2 output schema에 필드 없음 | 스키마에 추가 + 원본 기사 fallback |
| 4 | SK에코 sources URL이 가짜 | 프롬프트에 기사 URL 미전달 | Stage 2/4 프롬프트에 URL 포함 |
| 5 | `_parse_json`이 ` ```json` 처리 못 함 | 첫 줄만 split | `{}`범위 추출 로직 추가 |
| 6 | 상수 3곳 중복 정의 | html/md 렌더러 + filter | `constants.py` 공용 모듈로 통합 |
| 7 | `SKIP_DOMAINS` dead code | 정의만 하고 미사용 | `_is_uncrawlable()` 함수에서 활용 |
| 8 | **오래된 기사 혼입 (수개월 전)** | GNews 날짜 필터 없음 | `when:2d` + freshness 스코어링 |
| 9 | **소스 다양성 S1~S5 전무** | 필터링에서 전문매체 탈락 | `_ensure_source_minimum()` 추가 |
| 10 | `.env` 로드 안 됨 | `load_dotenv()` 누락 | `setup_logging()`에서 호출 |
| 11 | Windows cp949 인코딩 에러 | StreamHandler 기본 인코딩 | UTF-8 강제 |

---

## 의도 적합성 분석 결과

### 잘 작동하는 것
- ✅ 날짜 필터 → 최근 기사만 수집 (이전: 수개월 전 기사 혼입)
- ✅ Top 5 품질 → 실제 당일 뉴스 (SK에코 IPO 전환, 삼성 유보금, HBM4)
- ✅ 임원 브리핑 포맷 → Fact/Impact/Risk/Next Signal 4요소
- ✅ SK에코플랜트 렌즈 → 4대 축 + "주장(Claim)" 표기
- ✅ 브리핑 섹션 구조 → INITIAL-SCOPE.md 설계대로

### 남은 과제
- ⚠️ Google News URL 디코딩 → 본문 크롤링 여전히 실패 (전부 스니펫 fallback)
- ⚠️ 소스 다양성 → S1/S2 전문매체 추가 로직 있으나 실효성 검증 필요
- ⚠️ 카테고리 세분화 → 16개 서브스코프 중 5~6개만 독립 카테고리로 존재
- ⚠️ 카테고리별 요약 깊이 → Top 5만 Impact/Risk 있고, 나머지는 headline+fact만
- 🔲 동적 HTML 테마 → 사용자 의도와 다름, MVP 이후 재설계
- 🔲 웹 배포 (Phase 7)

---

## CLI 사용법

```bash
# Phase 5: 뉴스 수집
python -m src.main collect --date 2026-02-22

# Phase 6: 브리핑 생성
python -m src.main brief --date 2026-02-22

# 전체 테스트
python -m pytest tests/ -v
```

---

## 코드 구조 (현재 전체)

```
src/
  main.py                     # CLI: parse, preprocess, summarize, build-profile, collect, brief
  config.py                   # 경로/상수
  models/
    conversation.py           # Message, Conversation
    summary.py                # MicroSummary, StableProfile
    article.py                # Article (Phase 5)
  parser/                     # Phase 1
  preprocess/                 # Phase 2
  summarizer/                 # Phase 3
  profiler/                   # Phase 4
  collector/                  # Phase 5
    gnews_client.py            # Google News RSS 검색 (NewsAPI 대체)
    rss_client.py              # RSS 피드 구독
    query_builder.py           # 프로필 → 검색 쿼리
    article_filter.py          # 스코어링/필터링
    dedup.py                   # 중복 제거
    news_api_client.py         # (비활성 — 유료 전환 시 재활용)
  briefer/                    # Phase 6
    briefing_generator.py      # 4단계 LLM 파이프라인
    prompts.py                 # 프롬프트 템플릿
    article_crawler.py         # 기사 본문 크롤링
    markdown_renderer.py       # JSON → Markdown
    html_renderer.py           # JSON → HTML
    constants.py               # 공용 상수
  data/
    keywords.json
    rss_feeds.json             # RSS 피드 12개

output/
  stable_profile.json          # Phase 4 산출물
  collected/YYYY-MM-DD.json    # Phase 5 산출물
  briefings/
    YYYY-MM-DD.json            # 구조화된 브리핑
    YYYY-MM-DD.md              # 텍스트 브리핑
    YYYY-MM-DD.html            # 웹 UI 브리핑

tests/
  test_parser.py               # Phase 1 (7개)
  test_preprocess.py           # Phase 2 (24개)
  test_profiler.py             # Phase 4 (17개)
  test_collector.py            # Phase 5 (16개)
```

**테스트**: 86개 전체 통과

---

## 의존성

```
pytest>=8.0
anthropic>=0.80
python-dotenv>=1.0
feedparser>=6.0
requests>=2.31
beautifulsoup4>=4.12
```

---

## Phase 7 (다음 단계): 웹 배포

### MVP 범위

1. `output/briefings/YYYY-MM-DD.html`을 정적 사이트로 배포
2. GitHub Pages 또는 Vercel
3. 날짜별 네비게이션 (이전/다음)
4. 모바일 반응형 확인

### 향후 개선 (MVP 이후)

- Google News URL 디코더 (headless browser 또는 전용 라이브러리)
- 동적 HTML 테마 재설계 (사용자 의도에 맞게)
- 카테고리 세분화 (16개 서브스코프 복원)
- 카테고리별 요약에 Impact 추가
- 자동 스케줄링 (매일 05:00 KST 자동 실행)
- 결과 전달 (이메일/텔레그램)

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- 기존 코드 스타일 유지 (dataclass, type hints, to_dict 패턴)
- 테스트 작성 후 `python -m pytest tests/ -v`로 전체 통과 확인
- 네트워크 요청에 타임아웃(10~15초)과 재시도(최대 3회) 적용
