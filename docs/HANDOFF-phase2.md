# Phase 2 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 2 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. 아버지(건설/반도체/DC 인프라 업계 임원)가 매일 아침 5~20분 안에 핵심 뉴스를 파악하도록 자동 브리핑을 제공하는 시스템.

현재 만들고 있는 것은 **Program #1: ChatGPT Export Analyzer** — 아버지의 ChatGPT export zip에서 Stable Profile(고정 선호/관심/금기)을 자동 추출하는 파이프라인.

**핵심 맥락:**
- 아버지 대화: 약 46개, 평균 5문답 → 소량이므로 **토큰 효율보다 정확한 컨텍스트 추출**에 집중
- 아버지 설문 결과(`docs/father-profile-raw.md`)가 이미 확보됨
- ChatGPT export zip은 아직 도착 대기 중

---

## Phase 1 완료 상태 (구현됨, 테스트 7/7 통과)

### 구현된 파일들

```
src/
  __init__.py
  config.py                     # 경로/상수 설정, ensure_output_dirs()
  main.py                       # CLI (현재 parse 서브커맨드만 구현)
  models/
    __init__.py                 # re-export
    conversation.py             # Message, Conversation, ConversationChunk, ConversationMeta
    summary.py                  # MicroSummary, StableProfile
  parser/
    __init__.py
    zip_explorer.py             # ZIP 탐색, conversations.json 추출
    conversation_parser.py      # mapping 트리 → 선형 메시지 변환 (엣지 케이스 처리)
  preprocess/
    __init__.py                 # 비어있음
  summarizer/
    __init__.py                 # 비어있음
  profiler/
    __init__.py                 # 비어있음
  data/                         # 비어있음
tests/
  __init__.py
  fixtures/
    sample_conversations.json   # 4가지 케이스 (정상/짧은/빈/분기)
  test_parser.py                # 7개 테스트 전부 통과
output/                         # .gitignore 대상
```

### 주요 설계 결정
- conversations.json의 `mapping`은 트리 구조 → DFS 순회로 선형 변환
- 분기 대화: 최신 timestamp 자식만 추적
- `tool` role, `code` content_type은 건너뜀
- 루트 노드 message: null 처리, 비문자열 parts는 `[NON_TEXT_CONTENT]`

---

## 지금 해야 할 작업: Phase 2 + 선행 작업

### 작업 목록 (순서대로)

#### 2-0. 선행: father-profile-raw.json 생성 (수동 변환)
- `docs/father-profile-raw.md` (설문 원본)을 읽고 구조화된 JSON으로 변환
- 저장 위치: `docs/father-profile-raw.json`
- 스키마:

```json
{
  "basic": {
    "purpose": "all",
    "reading_time": "20min",
    "schedule": "early_morning_5_6",
    "weekend": true,
    "format": "list",
    "language": "summary_kr",
    "paywall": false
  },
  "industries": {
    "fab_capex": 3, "cleanroom": 3, "equipment_supply": 2, "packaging": 2,
    "memory_foundry": 2, "dc_build": 3, "dc_power": 3, "dc_cooling": 3,
    "dc_cloud": 2, "power_grid": 2, "renewable": 2, "nuclear": 2,
    "carbon_esg": 2, "petrochemical": 2, "battery_ev": 2, "bio_pharma": 2,
    "defense": 2, "transport_logistics": 2, "urban_smartcity": 3
  },
  "themes": {
    "epc_award": 3, "schedule_cost": 3, "permit": 3, "material_labor": 3,
    "safety": 2, "milestone": 3, "capex_guidance": 3, "pf_finance": 3,
    "contingent": 3, "ipo": 2, "ma_restructure": 3, "credit_bond": 2,
    "policy_subsidy": 2, "geopolitics": 2, "macro": 2, "trade_supply": 2,
    "esg_regulation": 3, "ai_trend": 2, "construction_tech": 3, "talent_hr": 3
  },
  "companies": {
    "sk_ecoplant": 3, "sk_group": 3, "kr_construction": 2,
    "semi_makers": 2, "hyperscalers": 2, "semi_equip": 2, "infra_equip": 3
  },
  "regions": ["korea", "us", "asia"],
  "triggers": ["large_award", "refinance"],
  "sk_lens": ["order_mix", "cashflow", "pf_contingent", "competitor"],
  "avoid_style": ["too_basic", "biased", "no_source"]
}
```

#### 2-1. 선행: keywords.json 생성
- `docs/initial_design/INITIAL-SCOPE.md`의 키워드 세트 + 설문 3점 항목에서 추출
- 저장 위치: `src/data/keywords.json`
- 스키마:

```json
{
  "industries": {
    "반도체": ["팹", "Fab", "증설", "CapEx", "클린룸", "UPW", "CDA", "스크러버"],
    "데이터센터": ["하이퍼스케일", "코로케이션", "캠퍼스", "MW"],
    "스마트시티": ["신도시", "복합개발", "스마트 인프라"],
    ...
  },
  "entities": ["SK에코플랜트", "SK ecoplant", "TSMC", "삼성전자", "Schneider", "Vertiv", ...],
  "themes": ["수주", "EPC", "낙찰", "PF", "우발채무", "자금보충", "ESG", "모듈러", "DfMA", ...],
  "format_hints": ["표", "요약", "리스트", "브리핑", "딥리드"],
  "avoid_signals": ["추측", "출처불명", "기초적", "편향", "홍보"],
  "question_patterns": ["어떻게", "왜", "비교", "추천", "전망", "리스크"]
}
```

#### 2-2. PII Masker 구현
- 파일: `src/preprocess/pii_masker.py`
- 정규식으로 한국 전화번호, 이메일, 주소 패턴, 계좌번호, 주민번호 마스킹
- `[PHONE]`, `[EMAIL]`, `[ADDRESS]`, `[ACCOUNT]`, `[SSN]` 플레이스홀더로 치환
- 입력: `list[Message]` → 출력: `list[Message]` (새 객체, 원본 불변)

#### 2-3. Chunker 구현
- 파일: `src/preprocess/chunker.py`
- **기본 전략: 대화 1개 = ConversationChunk 1개** (46개 대화, 평균 5문답이라 분할 불필요)
- 예외: `config.MAX_CHUNK_CHARS`(24,000자) 초과 시만 메시지 경계에서 분할
- 입력: `Conversation` → 출력: `list[ConversationChunk]`

#### 2-4. main.py에 preprocess 서브커맨드 추가
- `python -m src.main preprocess` 실행 시:
  1. `output/parsed_conversations.json` 로드
  2. PII 마스킹 적용
  3. Chunking
  4. `output/preprocessed_chunks.json` 저장
  5. `pipeline_state.json` 업데이트

#### 2-5. 테스트 작성
- `tests/test_preprocess.py` — PII 마스킹, chunking 단위 테스트

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `docs/father-profile-raw.md` | 아버지 설문 원본 (3/2/1 점수 + 지역/트리거/금지 등) |
| `docs/initial_design/INITIAL-SCOPE.md` | 키워드 세트, 쿼리 템플릿, 소스군 정의 |
| `docs/initial_design/EXTRACT-existing-GPT-context-plan.md` | Program #1 설계 원본 |
| `docs/initial_design/STABLE-PROFILE-extract-template.md` | Stable Profile 추출 시스템 프롬프트 + 설문 폼 |
| `src/config.py` | 경로 상수 (OUTPUT_DIR, MAX_CHUNK_CHARS 등) |
| `src/models/conversation.py` | Message, Conversation, ConversationChunk 정의 |
| `tests/fixtures/sample_conversations.json` | 테스트용 4개 대화 (정상/짧은/빈/분기) |

---

## 전체 설계 문서

전체 설계는 `.cursor/plans/program1_export_analyzer_*.plan.md`에 있다. 위 내용은 Phase 2 진행에 필요한 부분만 발췌한 것.

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- 테스트 통과 확인 후 다음 단계
- 기존 코드 스타일(dataclass, type hints, to_dict 패턴) 유지
