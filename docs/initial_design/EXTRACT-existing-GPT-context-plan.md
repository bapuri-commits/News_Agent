# ChatGPT Export 기반 컨텍스트 추출 계획

> 아버지 계정의 ChatGPT 대화에서 Stable Profile을 자동 추출하는 전체 전략 + Program #1 스펙

---

## 1. 진행 순서

### Step 1: 아버지 Stable Profile 확보
- 설문 + 기존 ChatGPT 컨텍스트 추출
- 산출물: `stable_profile.json`, 대화 컨텍스트 힌트 정책(lookback/weight) 기본값

### Step 2: 초기 스코프 세트 + SK에코플랜트 관전 오버레이 결합
- 프로필이 정해진 뒤 스코프를 붙이면 "폭은 넓되, 읽는 방식(렌즈)"이 고정돼서 편향이 덜 생김
- 산출물: 토픽 트리/키워드/쿼리/소스군 + SK에코플랜트 관전 렌즈

### Step 3: 설계 + 뼈대 구현 계획 산출
- 프로필/스코프가 고정된 상태에서 모듈/DB/가드레일/보안 구성
- 산출물: 모듈 구조, DB 스키마, 다양성 규칙, 스케줄러 흐름, VPS+VPN 보안 옵션

### Step 4: 튜닝 루프 (운영 시작 후)
- 소스군 보완 → 쿼리 정교화 → 랭킹 가중치 미세조정
- 대화 컨텍스트는 끝까지 얕게(5~10%) 유지

---

## 2. 대화가 많을 때의 처리 전략

### 전략 A: 2단 압축 파이프라인 (권장, 대화 100개여도 처리 가능)

원문 전체를 모델에 넣지 않고, Stable Profile에 필요한 신호만 자동 추출:

1. **(A) 대화별/청크별 micro-summary 생성**
   - 관심 주제 TOP3
   - 자주 묻는 질문 유형
   - 싫어하는 답변/형식(금기)
   - 원하는 출력 포맷
   - 의사결정 렌즈(리스크/기회/다음 신호)

2. **(B) micro-summary만 모아 meta-summary(통합)**
   - 최종 산출물: `stable_profile.json` + `ConversationHint 정책` + `Open Questions`
   - 장점: 토큰 효율↑ / 환각↓ / 보안↑(원문 전송 최소화)

### 전략 B: 수동 Export → 자동 Chunking → 일괄 요약

- ChatGPT "데이터 내보내기(export)" 후 로컬 처리
- 또는 최근 20개만 필터링 후 투입

### 전략 C: 브라우저 스크래핑 (최후 옵션 — 비권장)

- 세션/2FA/DOM 변경에 취약, 유지보수 지옥
- 결론: Export 기반이 더 안정적

---

## 3. 여러 대화창 문제 해결: Export(zip) 기반

- 아버지 계정에 대화가 여러 채팅방에 분산 → 수동 복붙은 비효율
- **공식 데이터 내보내기(Export) zip** 한 번으로 해결

**운영안:**
1. **초기 1회**: Export(zip) → Stable Profile 생성
2. **유지**: 뉴스/브리핑 관련 대화는 전용 채팅방으로 유도
3. **선택**: 1~3개월 단위로 Export 재수집하여 profile refresh

---

## 4. Program #1: ChatGPT Export Analyzer

### 목표
- **Input**: ChatGPT Export `.zip`
- **Output**:
  1. `conversation_index.json` — 대화 메타 목록 (제목/날짜/토큰/태그)
  2. `micro_summaries/*.jsonl` — 대화별 마이크로 요약 로그
  3. `stable_profile.json` — 통합 Stable Profile
  4. `evidence_pack/` — 근거 레퍼런스 (선택)

### 파이프라인

```
ZIP 파싱 → 대화 데이터 탐지 → 표준 모델 변환 → PII 마스킹 → Chunking → Micro-summary → Meta-summary
```

| 단계 | 설명 |
|------|------|
| **Step A** | ZIP 열기 → 내부 파일 구조 탐색 → 대화 데이터(JSON/HTML) 탐지 → 대화 단위 로딩 |
| **Step B** | PII 마스킹(전화/메일/주소/계좌), chunking(3k~8k tokens), 뉴스/브리핑 관련 필터 |
| **Step C** | Micro-summary 생성 (대화/청크별 관심축, 선호포맷, 금기, 의사결정 렌즈 추출) |
| **Step D** | Meta-summary 통합 → `stable_profile.json` 생성 |

### 표준 대화 모델

```json
{
  "conversation_id": "string",
  "title": "string",
  "created_at": "ISO-8601",
  "messages": [
    { "role": "user|assistant", "timestamp": "ISO-8601", "text": "string" }
  ]
}
```

### Micro-summary JSON 스키마

```json
{
  "conversation_id": "string",
  "title": "string",
  "time_range": { "start": "YYYY-MM-DD", "end": "YYYY-MM-DD" },
  "signals": {
    "topics_top": ["..."],
    "entities_top": ["..."],
    "preferred_format": ["5min_top5", "20min_deep", "tables", "links"],
    "avoid": ["clickbait", "no-sources", "speculation-heavy"],
    "decision_lens": ["risks", "opportunities", "next_signals"],
    "confidence": 0.0
  },
  "evidence_refs": [
    { "msg_index_range": [10, 18], "quote_snippet": "<=120 chars" }
  ]
}
```

### Stable Profile JSON 스키마 (최종 산출물)

```json
{
  "user_intent": "executive morning briefing",
  "top_priorities": [
    "semiconductor fab capex",
    "data center power/permitting",
    "construction awards",
    "finance/IPO"
  ],
  "must_include_triggers": [
    "large award",
    "refinancing/credit action",
    "PF contingent change",
    "IPO official signal"
  ],
  "avoid": ["bias amplification", "unsupported claims", "sensational tone"],
  "preferred_format": {
    "reading_time": "5min+20min",
    "sections": ["Top5", "ByCategory", "Risks", "NextSignals", "SourceDiversity"],
    "style": "executive_brief"
  },
  "conversation_hint_policy": { "lookback_days": 7, "max_weight_percent": 10 },
  "risk_guardrails": {
    "diversity_enforced": true,
    "require_links": true,
    "separate_fact_inference": true
  },
  "open_questions": ["..."]
}
```

### 구현 스택 (초기)

- **런타임**: Windows 로컬 Python CLI → 이후 VPS 이관 가능하게 모듈화
- **핵심 패키지**: `zipfile`, `json`, `sqlite3` (+ 추후 `fastapi`)
- **LLM 호출**: 플러그형 설계
  - (A) LLM 호출 모드
  - (B) 규칙 기반 임시 모드

---

## 5. Cursor 프롬프트 요약 (3종)

### 프롬프트 1: 2단 압축 파이프라인 설계
- 대화 N개(수십~수백) 입력 → micro-summary → Stable Profile JSON
- 필수 산출물: JSON 스키마, chunking 규칙, 중복/노이즈 제거, PII 필터링

### 프롬프트 2: Export 기반 ingestion 전략 고정
- 수동 복붙 불가 전제, Export zip 기반 자동 파싱
- UI 스크래핑은 최후 옵션으로만 언급

### 프롬프트 3: Program #1 구현 계획 (Export Analyzer)
- ZIP ingest → 분석 → Stable Profile JSON 생성
- 폴더 구조, 데이터 모델, 예시 입출력, 테스트 시나리오 포함

---

## 6. 운영 현실 (초기 속도 + 안정성)

| 시기 | 범위 |
|------|------|
| **처음 1~2주** | 아버지 관련/뉴스 브리핑 관련 대화만 우선 추출/분석 (빠른 MVP) |
| **그 다음** | Export 기반 자동 파이프라인 정식 운영 (대화 N개 확장) |

**최종 로드맵 한 줄:**
> Program #1(Export Analyzer) → stable_profile.json 확보 → 스코프/렌즈 결합 → 뉴스 브리핑 에이전트 설계/구현 → 1~2주 튜닝
