# News_Agent 향후 개선 과제 백로그

> 작성일: 2026-02-22
> Phase 6 완료 후 구현 감사에서 발견된 개선 과제 + 장기 기능 로드맵.
> 각 과제는 독립적으로 진행 가능하며, 새 세션에서 이 문서를 참조하면 맥락을 파악할 수 있다.

---

## 1. 본문 크롤링 개선

**우선순위**: 높음
**관련 파일**: `src/briefer/article_crawler.py`

### 현상

Google News RSS에서 수집된 기사 URL은 `news.google.com/rss/articles/...` 형식인데, 이건 JS 기반 redirect라 `requests.get()`으로 실제 기사 URL을 따라갈 수 없다. 현재 `resolve_google_news_url()`이 GET 요청 + HTML 파싱을 시도하지만 대부분 실패한다.

결과적으로 Top 5 기사도 전부 **스니펫(500자) fallback**으로 브리핑이 생성되어, Stage 2 (Opus) 심층 요약의 품질이 제한된다.

### 현재 코드의 시도

```python
def resolve_google_news_url(url):
    # GET 요청으로 리다이렉트 따라가기
    resp = requests.get(url, allow_redirects=True)
    # HTML에서 실제 URL 링크 추출
    soup = BeautifulSoup(resp.text, "html.parser")
    for a_tag in soup.find_all("a", href=True):
        ...
```

### 해결 방안

**방안 A: `gnews` 파이썬 라이브러리 활용**
- `pip install gnews` — Google News URL 디코더 내장
- Google News의 base64 인코딩된 URL을 자동 디코딩
- 가장 간단하지만 라이브러리 유지보수 의존

**방안 B: Playwright headless browser**
- `pip install playwright && playwright install chromium`
- JS 렌더링 후 최종 URL 추출
- 모든 사이트에서 동작하지만 느리고 무거움 (브라우저 프로세스)
- Top 5 (최대 5건)만 크롤링하므로 비용 허용 가능

**방안 C: Google News URL Base64 직접 디코딩**
- Google News URL의 path 부분이 base64 인코딩된 실제 URL
- `CBMi...` 패턴을 디코딩하면 원본 URL 추출 가능
- 외부 의존성 없음, 가장 가벼움
- Google이 인코딩 방식을 변경하면 깨질 수 있음

### 구현 계획

1. 방안 C를 먼저 시도 (base64 디코딩)
2. 실패율이 높으면 방안 A로 전환
3. `fetch_body()`에서 크롤링 성공/실패를 로깅하여 성공률 모니터링
4. 크롤링 성공 시 본문을 `MAX_BODY_CHARS`(3000자)로 잘라서 전달

### 기대 효과

- Top 5 기사 본문 크롤링률: 0% → 70~90%
- Stage 2 (Opus) 요약 품질 대폭 향상
- Fact 섹션에 구체적 수치/금액/일정이 포함됨

---

## 2. 카테고리별 요약 심화

**우선순위**: 중간
**관련 파일**: `src/briefer/prompts.py` (Stage 3), `src/briefer/briefing_generator.py`

### 현상

현재 브리핑의 카테고리별 요약(Stage 3)은 `headline + fact` 2줄 구조. Top 5만 `Fact/Impact/Risk/Next Signal` 4요소가 있다.

INITIAL-SCOPE.md의 "임원 브리핑 강제 포맷"은 **모든 기사**에 4요소를 기대하지만, 30~50건 전부에 적용하면 LLM 비용과 브리핑 길이가 과도해진다.

### 해결 방안

**방안 A: 카테고리 요약에 Impact 1줄 추가**
- Stage 3 output schema에 `impact` 필드 추가
- `headline + fact + impact` 3줄 구조
- 비용 증가 미미 (Sonnet 사용)

**방안 B: 중요 카테고리만 심층 분석**
- `score 3` 카테고리(fab_capex, dc_build, epc_award 등)만 Stage 2와 동일한 4요소 적용
- `score 2` 카테고리는 현행 유지
- Stage 3를 2번 호출 (심층 + 간략)

### 구현 계획

1. 방안 A를 먼저 적용 (Stage 3 프롬프트 수정)
2. `STAGE3_OUTPUT_SCHEMA`에 `impact` 필드 추가
3. `markdown_renderer.py`와 `html_renderer.py`의 카테고리 렌더링 부분 수정
4. 결과물 검토 후 방안 B 결정

### 수정 대상 코드

```python
# prompts.py - STAGE3_OUTPUT_SCHEMA 수정
"items": [
    {
        "id": "기사id",
        "headline": "한줄 요약",
        "fact": "핵심 사실 (1문장)",
        "impact": "업계 영향 (1문장)"   # ← 추가
    }
]
```

---

## 3. 뉴스 수집 튜닝

**우선순위**: 중간
**관련 파일**: `src/collector/article_filter.py`, `src/collector/query_builder.py`

### 현상

키워드 매칭 기반 스코어링(`_KEYWORD_MAP`)으로 노이즈가 존재한다:
- "power"가 dc_power와 매칭되지만 "purchasing power" 같은 비관련 기사도 포함
- "contract"가 epc_award와 매칭되지만 스마트폰 계약 기사도 포함
- 소스 다양성 보장 로직(`_ensure_source_minimum`)이 실효성 불확실 (S1/S2 기사의 freshness 패널티로 score 0 → 임계값 미통과)

### 해결 방안

**단기 (키워드 튜닝)**
- `_KEYWORD_MAP`의 키워드를 2-gram으로 확장 (예: "power" → "dc power", "power grid")
- 단독으로 너무 일반적인 키워드 제거 또는 가중치 하향
- `_score_freshness` 로직 조정: RSS 전문매체(S1/S2)에는 freshness 패널티 완화

**중기 (LLM 필터)**
- 수집 후 1차 필터에 경량 모델(Haiku) 적용
- "이 기사가 반도체/DC/건설 업계 임원에게 관련 있는가?" → Yes/No 판정
- 비용: Haiku로 50건 × ~200 토큰 = ~$0.01/일

**장기 (피드백 루프)**
- 사용자 피드백으로 키워드 가중치 자동 조정 (과제 4와 연결)

### 기술 부채

| 항목 | 설명 |
|------|------|
| `_KEYWORD_MAP` 중복 | `"capex"`가 `fab_capex`와 `capex_guidance`에 중복 매핑 |
| 단일 키워드 오탐 | "power", "contract", "award" 등 단독 사용 시 false positive |
| S7 과대 비중 | 국내매체 30건/37건(81%) — 영어권 기사 비중 확대 필요 |
| `MINORITY_MIN` 미보장 | 전문매체 기사가 freshness 패널티로 score 0이면 보장 로직 통과 못 함 |

---

## 4. 사용자 피드백 채팅 기능

**우선순위**: 낮음 (MVP 이후)
**관련 파일**: 신규 모듈 필요

### 목적

아버지가 브리핑을 보면서 "이건 관련 없어", "이 토픽 더 보고 싶어"를 말하면 프로필/스코어링에 자동 반영. `stable_profile.json`의 `conversation_hint_policy` (lookback_days: 7, max_weight_percent: 10)를 활용.

### 아키텍처

```
브리핑 웹 페이지
  └─ 채팅/피드백 UI (하단 플로팅 버튼)
       ↓
[REST API 또는 로컬 JSON 저장]
  └─ feedback/YYYY-MM-DD.json
       ↓
[피드백 처리기]
  └─ stable_profile.json 가중치 미세 조정
       - 관련 없다고 한 카테고리: -0.05 (최대 -0.3)
       - 더 보고 싶다고 한 카테고리: +0.05 (최대 +0.3)
       - 7일 지나면 조정치 decay
       - 전체 조정치 합이 원래 스코어의 10% 이내 (편향 방지)
```

### 피드백 유형

| 유형 | UI | 효과 |
|------|-----|------|
| 👎 관련 없음 | 기사 카드에 버튼 | 해당 카테고리 가중치 -0.05 |
| 👍 유용함 | 기사 카드에 버튼 | 해당 카테고리 가중치 +0.05 |
| "더 보고 싶음" | 카테고리 배지에 버튼 | 해당 카테고리 score +0.1 |
| "줄여줘" | 카테고리 배지에 버튼 | 해당 카테고리 score -0.1 |
| 자유 텍스트 | 채팅 입력 | LLM이 해석 → 구조화된 피드백으로 변환 |

### 구현 단계

1. `FeedbackEntry` 데이터 모델 (dataclass)
2. `feedback/YYYY-MM-DD.json` 저장소
3. `profile_adjuster.py` — 피드백 → 프로필 가중치 조정
4. 브리핑 HTML에 피드백 버튼 삽입 (JS로 로컬 저장 또는 API 호출)
5. `collect` 실행 시 최근 7일 피드백 반영

### 의존성

- Phase 7 (웹 배포) 완료 후 진행
- 서버가 필요하면 Vercel Serverless Functions 또는 GitHub Issues API 활용 (서버리스)
- 서버 없이 하려면 GitHub Issues에 피드백을 이슈로 자동 생성하고 파이프라인에서 읽는 방식

---

## 5. 검색용 채팅 기능

**우선순위**: 낮음 (MVP 이후)
**관련 파일**: 신규 모듈 필요

### 목적

"지난주 반도체 수주 관련 뉴스 보여줘", "SK에코플랜트 IPO 관련 뉴스 모아줘" 같은 자연어 질의에 답변. 과거 브리핑 데이터를 검색 소스로 활용.

### 아키텍처

```
사용자 질의: "이번달 데이터센터 수주 뉴스"
    ↓
[질의 분석] LLM이 키워드 + 날짜 범위 + 카테고리 추출
    ↓
[검색] briefings/*.json에서 매칭
    - 날짜 범위 필터
    - 카테고리 필터 (by_category 키)
    - 키워드 전문 검색 (headline, fact, summary)
    ↓
[답변 생성] LLM이 검색 결과를 자연어로 정리
    ↓
채팅 UI에 표시
```

### 데이터 소스

```
output/briefings/
  ├─ 2026-02-20.json  ← 검색 대상
  ├─ 2026-02-21.json
  ├─ 2026-02-22.json
  └─ ...
```

각 JSON에는 `top5`, `by_category`, `sk_ecoplant`, `risks`, `next_signals`가 구조화되어 있어 검색에 적합.

### 구현 단계

1. **브리핑 아카이브 인덱서**: `briefings/*.json`을 스캔하여 검색용 인덱스 생성
   - 날짜, 카테고리, 키워드, 헤드라인을 플랫하게 펼침
   - SQLite FTS5 또는 단순 JSON 인덱스
2. **검색 API**: 키워드 + 날짜 범위 + 카테고리 필터
3. **RAG 파이프라인**: 질의 → 검색 → LLM 답변 생성
4. **채팅 UI**: 웹 페이지 내 채팅 위젯 (React/Vue 또는 바닐라 JS)

### 기술 선택지

| 방식 | 장점 | 단점 |
|------|------|------|
| JSON 파일 직접 검색 | 서버 불필요, 심플 | 데이터 많아지면 느림 |
| SQLite FTS5 | 전문 검색, 빠름 | 서버 필요 (또는 WASM) |
| Vercel + Edge Functions | 서버리스, 무료 | 복잡도 증가 |
| 클라이언트 사이드 JS | 서버 불필요 | JSON 전체 로드 필요 |

MVP는 클라이언트 사이드 JS로 briefings/*.json을 직접 검색하는 방식이 가장 간단.

---

## 6. HTML 테마 재설계

**우선순위**: 낮음
**관련 파일**: `src/briefer/html_renderer.py`

### 현상

현재 6가지 동적 테마(Tech Blue, Infra Purple, Deal Green, Risk Red, SK Orange, Market Teal)가 콘텐츠의 지배적 카테고리에 따라 자동 선택된다. 사용자 피드백: **"원하던 방식이 아님"** — MVP에서는 보류.

### 사용자 의도 (추정)

"매번 다른 스타일의 브리핑" = 단순 색상 변경이 아니라:
- 레이아웃/구조가 내용에 따라 달라짐
- 리스크가 많은 날은 경고 느낌의 레이아웃
- SK에코플랜트 뉴스가 핵심인 날은 SK 전용 대시보드 느낌
- 일반적인 날은 클린한 뉴스레터 느낌

### 해결 방안

**방안 A: 레이아웃 템플릿 분기**
- 3~4가지 HTML 템플릿 (뉴스레터형, 대시보드형, 경고형, SK 포커스형)
- 콘텐츠 분석 후 적절한 템플릿 선택
- 단점: 유지보수할 HTML이 3~4배

**방안 B: CSS 클래스 기반 변형**
- 하나의 HTML 구조에서 `body` 클래스만 변경 (`layout-newsletter`, `layout-dashboard` 등)
- CSS에서 클래스별 레이아웃 차이 정의
- 장점: HTML 하나, CSS만 분기

**방안 C: 사용자에게 정확한 의도 재확인**
- 다음 세션에서 사용자에게 "어떤 느낌을 원하는지" 레퍼런스 URL/이미지 요청
- 막연한 추측보다 구체적 방향 설정이 우선

### 현재 코드 (참고)

```python
# html_renderer.py
THEMES = {
    "tech_blue": {"bg": "#f0f4ff", "accent": "#1a73e8", ...},
    "risk_red": {"bg": "#fef2f2", "accent": "#dc2626", ...},
    ...
}

def _pick_theme(briefing: dict) -> dict:
    # 리스크 4건 이상 → risk_red
    # SK에코 5건+ → sk_orange
    # Fab/CapEx 지배 → tech_blue
    # ...
```

---

## 우선순위 요약

| # | 과제 | 우선순위 | 의존성 | 예상 공수 |
|---|------|---------|--------|----------|
| 1 | 본문 크롤링 개선 | **높음** | 없음 | 2~3시간 |
| 2 | 카테고리별 요약 심화 | 중간 | 없음 | 1~2시간 |
| 3 | 뉴스 수집 튜닝 | 중간 | 없음 | 2~4시간 |
| 4 | 사용자 피드백 채팅 | 낮음 | Phase 7 완료 | 6~8시간 |
| 5 | 검색용 채팅 | 낮음 | Phase 7 + 데이터 축적 | 8~12시간 |
| 6 | HTML 테마 재설계 | 낮음 | 사용자 의도 재확인 | 3~5시간 |

과제 1~3은 Phase 7과 병행 가능. 과제 4~6은 Phase 7 배포 이후.
