# Phase 5 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 5 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Program #1(Phase 1~4)로 Stable Profile 추출 완료. Phase 5부터는 Program #2 — 실제 뉴스 수집 파이프라인 구현.

**Phase 1~4 완료 상태:**
- Phase 1: ZIP 파싱 (65개 대화, 643개 메시지) — 완료
- Phase 2: PII 마스킹 + 청킹 (73개 chunk) — 완료
- Phase 3: Claude Opus로 micro-summary 추출 (28개 비즈니스) — 완료
- Phase 4: Profile Builder → `stable_profile.json` 확정 — 완료
  - open_questions 6개 전부 아버지 확인 완료, `confirmed_overrides` 반영

---

## Phase 5: News Collector — 해야 할 작업

### 목표

`output/stable_profile.json`의 키워드/토픽/엔티티 기반으로
→ **뉴스 API + RSS 피드** 하이브리드 수집
→ **`output/collected_articles.json`** (일자별 원시 기사 풀)

### 수집 아키텍처: API + RSS 하이브리드

```
stable_profile.json
  ├─ 키워드/토픽/엔티티 추출
  │
  ├─ [경로 A] News API 검색 (키워드 쿼리)
  │   └─ 글로벌 종합지 + 국내 뉴스
  │
  ├─ [경로 B] RSS 피드 구독 (전문매체)
  │   └─ DCD, EE Times, ENR, 전자신문 등
  │
  └─ 병합 → 중복 제거 → 프로필 기반 필터링/스코어링
      └─ collected_articles.json (20~50개/일)
```

### 구현할 파일

#### 1. `src/collector/__init__.py` — 빈 파일

#### 2. `src/collector/query_builder.py` — 프로필 → 검색 쿼리 생성

```python
def build_queries(profile: dict) -> list[dict]:
    """stable_profile.json에서 검색 쿼리 세트 생성.
    
    Returns:
        [{"category": "fab_capex", "query_en": "...", "query_kr": "...", "priority": 3}, ...]
    
    쿼리 설계 원칙:
    - top_priorities score 3 항목: 전용 쿼리 생성
    - score 2 항목: 상위 카테고리에 포함 (별도 쿼리 없음)
    - mode: "trigger" 항목: 이상 시그널 키워드 추가 (급등, 파업, 지연, 사고 등)
    - mode: "contextual" 항목: 별도 쿼리 없음 (관련 기사에서 자연 포착)
    - SK에코플랜트: 전용 쿼리 세트 (INITIAL-SCOPE.md의 D절 참고)
    """
```

쿼리 생성 규칙 (INITIAL-SCOPE.md 기반):

| 카테고리 | 쿼리 패턴 (EN) | 쿼리 패턴 (KR) |
|----------|----------------|----------------|
| Fab/CapEx | `(TSMC OR Samsung OR SK hynix OR Intel) AND (fab OR semiconductor plant) AND (capex OR expansion OR construction)` | `(반도체 OR 팹 OR 클린룸) AND (증설 OR 착공 OR 투자)` |
| DC 인프라 | `(data center OR hyperscale) AND (campus OR construction OR MW) AND (power OR cooling)` | `(데이터센터 OR 하이퍼스케일) AND (신축 OR 전력 OR 냉각)` |
| EPC/수주 | `(EPC OR contractor) AND (semiconductor OR data center) AND (award OR contract)` | `(EPC OR 수주 OR 계약) AND (반도체 OR 데이터센터)` |
| M&A | `(M&A OR acquisition OR divestiture) AND (semiconductor OR data center OR construction)` | `(M&A OR 인수 OR 매각) AND (반도체 OR 건설)` |
| SK에코플랜트 | `("SK ecoplant" OR "SK에코플랜트") AND (수주 OR EPC OR 차환 OR IPO OR PF)` | 동일 |
| ESG/탄소규제 | `(ESG OR carbon OR emission) AND (regulation OR investment OR credit)` | `(ESG OR 탄소 OR 배출권) AND (규제 OR 투자 OR 크레딧)` |

#### 3. `src/collector/news_api_client.py` — News API 수집

```python
class NewsAPIClient:
    """NewsAPI(newsapi.org) 또는 대안 API를 통한 뉴스 검색.
    
    - API_KEY는 .env에서 로드 (NEWS_API_KEY)
    - 일일 요청 제한 관리
    - 페이지네이션 처리
    - 결과를 Article 형태로 정규화
    """
    
    def search(self, query: str, language: str = "en",
               from_date: str = None, to_date: str = None) -> list[Article]:
        ...
```

API 선택 기준 (구현 시 확인):
- **NewsAPI** (newsapi.org): 무료 100회/일, 유료 월$50 (1000회/일). 한국어 지원 제한적.
- **대안**: GNews API, Currents API, 또는 Google News RSS 파싱
- 한국 뉴스: 네이버 뉴스 검색 API 또는 RSS 활용 검토

#### 4. `src/collector/rss_client.py` — RSS 피드 수집

```python
class RSSClient:
    """RSS 피드 구독 및 파싱.
    
    - feedparser 라이브러리 사용
    - 피드 목록은 src/data/rss_feeds.json에서 관리
    - 피드별 마지막 수집 시점 기록 (중복 방지)
    """
    
    def fetch_all(self, feeds: list[dict]) -> list[Article]:
        ...
    
    def fetch_feed(self, feed_url: str, since: str = None) -> list[Article]:
        ...
```

#### 5. `src/data/rss_feeds.json` — RSS 피드 목록

```json
{
  "feeds": [
    {"name": "DatacenterDynamics", "url": "https://www.datacenterdynamics.com/en/rss/", "source_group": "S1", "lang": "en"},
    {"name": "EE Times", "url": "https://www.eetimes.com/feed/", "source_group": "S2", "lang": "en"},
    {"name": "Semiconductor Engineering", "url": "https://semiengineering.com/feed/", "source_group": "S2", "lang": "en"},
    {"name": "ENR", "url": "https://www.enr.com/rss", "source_group": "S5", "lang": "en"},
    {"name": "Reuters Business", "url": "https://www.reutersagency.com/feed/", "source_group": "S6", "lang": "en"},
    {"name": "전자신문", "url": "https://rss.etnews.com/Section901.xml", "source_group": "S7", "lang": "kr"},
    {"name": "더일렉", "url": "https://www.thelec.kr/rss/allArticle.xml", "source_group": "S7", "lang": "kr"}
  ]
}
```

> 위 URL은 예시. 구현 시 실제 접근 가능한 피드 URL을 확인하고 업데이트할 것.

#### 6. `src/collector/article_filter.py` — 프로필 기반 필터링/스코어링

```python
def score_article(article: Article, profile: dict) -> float:
    """기사를 프로필 기준으로 관련도 스코어링 (0.0 ~ 1.0).
    
    스코어링 규칙:
    - top_priorities score 3 키워드 매치: +0.3
    - score 2 키워드 매치: +0.1
    - SK에코플랜트 직접 언급: +0.5
    - must_include_triggers 매치: +0.5 (무조건 포함)
    - avoid 항목 해당: -0.5
    - 소스 다양성 보너스: 소스군(S1~S7) 미출현군에서 오면 +0.1
    """

def filter_articles(articles: list[Article], profile: dict,
                    max_count: int = 50) -> list[Article]:
    """스코어링 후 상위 max_count개 선별.
    
    추가 규칙:
    - mode: "trigger" 항목: trigger_condition 키워드 매치 시에만 통과
    - mode: "contextual" 항목: 관련 카테고리 기사 내 자연 언급만 유지
    - 소스군 다양성: 단일 소스군이 전체의 40% 초과하지 않도록 리밸런싱
    """
```

#### 7. `src/collector/dedup.py` — 중복 제거

```python
def deduplicate(articles: list[Article]) -> list[Article]:
    """제목/URL 기반 중복 제거.
    
    - 완전 동일 URL 제거
    - 제목 유사도(Jaccard 또는 간단한 토큰 겹침) > 0.7이면 중복 판정
    - 중복 시 소스 신뢰도 높은 쪽 유지
    """
```

#### 8. `src/models/article.py` — Article 데이터 모델

```python
@dataclass
class Article:
    id: str                    # UUID
    title: str
    url: str
    source_name: str           # "DatacenterDynamics", "전자신문" 등
    source_group: str          # "S1" ~ "S7"
    published_at: str          # ISO 8601
    language: str              # "en" or "kr"
    snippet: str               # 본문 일부 또는 description (최대 500자)
    categories: list[str]      # 매칭된 프로필 카테고리 키
    relevance_score: float     # article_filter의 스코어
    collected_at: str           # 수집 시점
```

#### 9. `src/main.py`에 `collect` 서브커맨드 추가

```
python -m src.main collect [--date 2026-02-22]
```

1. `output/stable_profile.json` 로드
2. `build_queries()` → 검색 쿼리 세트 생성
3. `NewsAPIClient.search()` → API 기사 수집
4. `RSSClient.fetch_all()` → RSS 기사 수집
5. 병합 → `deduplicate()` → `filter_articles()` → 스코어링
6. `output/collected/YYYY-MM-DD.json` 저장
7. `pipeline_state.json` 업데이트

### 출력 스키마 — collected_articles

```json
{
  "date": "2026-02-22",
  "collection_stats": {
    "api_raw": 120,
    "rss_raw": 80,
    "after_dedup": 150,
    "after_filter": 45,
    "source_distribution": {"S1": 5, "S2": 8, "S5": 3, "S6": 12, "S7": 17}
  },
  "articles": [
    {
      "id": "...",
      "title": "TSMC Arizona Fab 2 — $40B Expansion on Track for 2027",
      "url": "https://...",
      "source_name": "Reuters",
      "source_group": "S6",
      "published_at": "2026-02-22T08:30:00Z",
      "language": "en",
      "snippet": "TSMC confirmed its second Arizona fab...",
      "categories": ["fab_capex", "semi_makers"],
      "relevance_score": 0.85,
      "collected_at": "2026-02-22T05:00:00+09:00"
    }
  ]
}
```

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `output/stable_profile.json` | 확정된 Stable Profile (Phase 4 산출물 + open_questions 확정) |
| `docs/initial_design/INITIAL-SCOPE.md` | 키워드 세트, 쿼리 템플릿, 소스군 정의 |
| `src/config.py` | 경로 상수 (확장 필요) |
| `src/models/summary.py` | 기존 데이터 모델 참고 (코딩 스타일) |
| `.env` | API 키 관리 (ANTHROPIC_API_KEY 있음, NEWS_API_KEY 추가 필요) |

---

## 구현된 코드 구조 (현재 상태 + Phase 5 추가분)

```
src/
  main.py                     # CLI: parse, preprocess, summarize, build-profile (+ collect 추가)
  config.py                   # 경로/상수 (확장 필요)
  models/
    conversation.py           # Message, Conversation 등
    summary.py                # MicroSummary, StableProfile
    article.py                # Article (신규)
  parser/                     # Phase 1 (완료)
  preprocess/                 # Phase 2 (완료)
  summarizer/                 # Phase 3 (완료)
  profiler/                   # Phase 4 (완료)
    survey_loader.py
    profile_builder.py
  collector/                  # Phase 5 (구현 필요)
    __init__.py
    query_builder.py           # 프로필 → 검색 쿼리
    news_api_client.py         # News API 수집
    rss_client.py              # RSS 피드 수집
    article_filter.py          # 스코어링/필터링
    dedup.py                   # 중복 제거
  data/
    keywords.json              # 기존
    rss_feeds.json             # RSS 피드 목록 (신규)
```

---

## 의존성 추가 필요

```
feedparser        # RSS 파싱
requests          # HTTP 요청 (News API + RSS)
python-dotenv     # .env 로드
```

기존 `requirements.txt` 확인 후 없으면 추가.

---

## 구현 순서 권장

1. `Article` 모델 + `config.py` 경로 추가
2. `rss_feeds.json` 생성 + `rss_client.py` (RSS부터 — 무료, API키 불필요)
3. `query_builder.py` (프로필 → 쿼리)
4. `news_api_client.py` (API 키 세팅 후)
5. `dedup.py` + `article_filter.py`
6. `main.py`에 `collect` 서브커맨드
7. 테스트 작성 + 실행
8. 실제 수집 테스트 → 결과 검토

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- 기존 코드 스타일 유지 (dataclass, type hints, to_dict 패턴)
- `.env`에 API 키 추가 시 `.env.example`도 업데이트
- 테스트 작성 후 `python -m pytest tests/ -v`로 전체 통과 확인
- RSS 피드 URL은 구현 시 실제 접근 가능 여부 확인 필수
- 네트워크 요청에는 적절한 타임아웃(10초)과 재시도(최대 3회) 적용
- User-Agent 헤더 설정 (봇 차단 방지)
