# Phase 4 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 4 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Program #1은 아버지의 ChatGPT export에서 Stable Profile을 추출하는 파이프라인이다.

**Phase 1~3 완료 상태:**
- Phase 1: ZIP 파싱 (65개 대화, 643개 메시지) — 완료
- Phase 2: PII 마스킹 + 청킹 (73개 chunk) — 완료
- Phase 3: Claude Opus로 micro-summary 추출 (28개 비즈니스 / 45개 비관련) — 완료

**전체 보고서:** `docs/PHASE3-REPORT.md` 참고

---

## Phase 4: Profile Builder — 해야 할 작업

### 목표

`output/micro_summaries/business_summaries.json` (28개 비즈니스 micro-summary)
+ `docs/father-profile-raw.json` (직접 설문 결과)
→ **`output/stable_profile.json`** (최종 Stable Profile)

### 구현할 파일

#### 1. `src/profiler/survey_loader.py` — 설문 JSON 로드

```python
def load_survey(path: Path) -> dict:
    """docs/father-profile-raw.json을 로드하여 반환."""
```

#### 2. `src/profiler/profile_builder.py` — 핵심 병합 로직

```python
def build_profile(summaries: list[MicroSummary], survey: dict) -> StableProfile:
    """micro-summary 집계 + 설문 병합 → StableProfile 생성."""
```

병합 규칙:

| 조건 | 처리 |
|------|------|
| 설문 3점 + export 빈출 | `top_priorities` 최고 우선, source: "both" |
| 설문 3점 + export 약함/미출현 | `top_priorities` 포함, source: "survey", `open_questions`에 기록 |
| 설문 2점 + export 빈출 | `top_priorities`로 격상, source: "both" |
| 설문 2점 + export 미출현 | 관심 수준 유지, `industries`/`themes`에 score 2로 기록 |
| export에만 등장 (설문 미선택) | `open_questions`에 "확인 필요" 항목으로 기록 |
| 충돌 시 | 설문 결과 우선 (명시적 선언 > 암묵적 패턴) |

집계 방법:
1. 28개 business micro-summary에서 `topics_top`, `entities_top`, `decision_lens` 빈도 카운팅
2. `keyword_matches`의 industries/entities/themes 빈도 합산
3. `preferred_format` 합집합 (설문 "리스트" + export "표/비교분석" → 모두 포함)
4. `avoid` 합집합
5. `evidence_refs`에서 confidence 0.8 이상인 대화의 핵심 인용 수집

특이 반영사항 (PHASE3-REPORT에서 발견):
- 포맷: 설문 "리스트" vs export "표+비교분석" → 둘 다 포함
- 도시개발/스마트시티: 설문 3점이나 export 약함 → open_questions
- ESG/탄소규제: 설문 3점이나 export 약함 → open_questions  
- 인프라장비(Schneider 등): 설문 3점 전용추적이나 export 약함 → open_questions
- 뉴스 브리핑 직접 요청 증거: user_intent에 반영

#### 3. `src/main.py`에 `build-profile` 서브커맨드 추가

```
python -m src.main build-profile
```

1. `output/micro_summaries/business_summaries.json` 로드
2. `docs/father-profile-raw.json` 로드
3. `build_profile()` 호출
4. `output/stable_profile.json` 저장
5. `pipeline_state.json` 업데이트

### StableProfile 최종 출력 스키마

```json
{
  "user_intent": "매일 아침 5~20분 내 반도체/DC/건설/투자 핵심 동향 파악. 직접 요청 증거: 'Send me semiconductor business news at 8am every day'",
  "top_priorities": [
    {"name": "반도체 Fab/CapEx", "score": 3, "source": "both", "export_mentions": 10},
    {"name": "데이터센터 인프라", "score": 3, "source": "both", "export_mentions": 3},
    {"name": "EPC/수주/건설", "score": 3, "source": "both", "export_mentions": 5},
    {"name": "SK그룹/하이닉스", "score": 3, "source": "both", "export_mentions": 5},
    {"name": "경영진 인사/조직", "score": 3, "source": "both", "export_mentions": 7},
    {"name": "M&A/사업재편", "score": 3, "source": "both", "export_mentions": 5},
    ...
  ],
  "must_include_triggers": ["large_award", "refinance"],
  "avoid": ["too_basic", "biased", "no_source"],
  "preferred_format": {
    "reading_time": "20min",
    "sections": ["Top5", "ByCategory", "Risks", "NextSignals", "SourceDiversity"],
    "style": "executive_brief",
    "detail_preferences": ["리스트", "표", "비교분석"]
  },
  "source_preferences": {
    "paywalled_ok": false,
    "language": "summary_kr"
  },
  "schedule": {
    "timezone": "Asia/Seoul",
    "daily_time": "05:00-06:00",
    "weekends": true
  },
  "industries": { "fab_capex": 3, "cleanroom": 3, ... },
  "themes": { "epc_award": 3, "schedule_cost": 3, ... },
  "companies": { "sk_ecoplant": 3, "sk_group": 3, ... },
  "regions": ["korea", "us", "asia"],
  "sk_ecoplant_lens": ["order_mix", "cashflow", "pf_contingent", "competitor"],
  "conversation_hint_policy": { "lookback_days": 7, "max_weight_percent": 10 },
  "risk_guardrails": {
    "diversity_enforced": true,
    "require_links": true,
    "separate_fact_inference": true
  },
  "open_questions": [
    "도시개발/스마트시티: 설문 3점이나 export에서 1건만 — 실제 관심도 확인 필요",
    "ESG/탄소규제: 설문 3점이나 export 약함 — 규제 관점 vs 적극적 관심 구분 필요",
    "인프라장비(Schneider/Vertiv): 설문 전용추적이나 export 약함 — 추적 수준 재확인",
    "포맷 선호: 설문 '리스트' vs export '표+비교분석' — 실사용 시 피드백으로 확정"
  ],
  "metadata": {
    "generated_at": "2026-02-22T...",
    "export_conversation_count": 65,
    "business_relevant_count": 28,
    "survey_date": "2026-02-18",
    "model_used": "claude-opus-4-6",
    "pipeline_version": "1.0"
  }
}
```

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `output/micro_summaries/business_summaries.json` | 28개 비즈니스 micro-summary (Phase 3 산출물) |
| `docs/father-profile-raw.json` | 직접 설문 결과 (구조화 JSON) |
| `docs/PHASE3-REPORT.md` | Phase 1~3 실행 보고서 |
| `src/models/summary.py` | MicroSummary, StableProfile dataclass 정의 |
| `src/config.py` | STABLE_PROFILE_PATH, SURVEY_PATH 등 경로 상수 |

---

## 구현된 코드 구조 (현재 상태)

```
src/
  main.py                     # CLI: parse, preprocess, summarize (+ build-profile 추가 예정)
  config.py                   # 경로/상수
  models/
    conversation.py           # Message, Conversation, ConversationChunk, ConversationMeta
    summary.py                # MicroSummary, StableProfile
  parser/                     # Phase 1 (완료)
  preprocess/                 # Phase 2 (완료)
  summarizer/                 # Phase 3 (완료)
    base.py                   # SummarizerBase, LLMProvider ABC
    llm_summarizer.py         # Claude Opus 구현
  profiler/                   # Phase 4 (구현 필요)
    __init__.py               # 비어있음
    survey_loader.py          # 구현 필요
    profile_builder.py        # 구현 필요
```

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- 기존 코드 스타일 유지 (dataclass, type hints, to_dict 패턴)
- StableProfile.to_dict()가 이미 정의되어 있음 — 필드 추가 시 함께 업데이트
- 테스트 작성 후 `python -m pytest tests/ -v`로 전체 통과 확인
- `output/stable_profile.json` 생성 후 내용을 보고하여 사용자 검토 받기
