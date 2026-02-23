# 피드백 + RAG 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 피드백 시스템과 RAG 챗봇 작업을 시작할 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Phase 1~8 완료 (프로필 추출 → 뉴스 수집 → 브리핑 생성 → 웹 배포 → 자동 스케줄링). 이번 작업에서 **VPS 백엔드**를 추가하여 두 가지 기능을 구현한다.

**배포 URL**: https://bapuri-commits.github.io/News_Agent/

---

## 구현할 기능 2가지

### 기능 1: 사용자 피드백 → 프로필 자동 반영

아버지가 브리핑을 읽으면서 👍/👎 클릭 + 카드 펼침/링크 클릭 행동을 VPS에 전송. 매일 brief 실행 전에 피드백을 자동 반영하여 `stable_profile.json` 가중치를 미세 조정.

### 기능 2: 검색 + 프롬프트 생성기

브리핑 아카이브를 검색하여 단순 질문에는 직접 답변하고, 심층 분석이 필요한 질문에는 관련 기사 + 프로필을 조합한 **ChatGPT용 프롬프트**를 생성하여 클립보드에 복사해주는 시스템.

---

## 아키텍처

```
[GitHub Pages — 정적 프론트엔드]
  브리핑 HTML (카드 UI)
    ├─ 👍/👎 버튼 → fetch POST /api/feedback
    ├─ 카드 펼침/링크 클릭 → fetch POST /api/feedback (암묵적)
    └─ 💬 챗 패널
        ├─ 단순 질의 → POST /api/chat → 결과 카드 표시
        └─ 심층 질의 → POST /api/prompt → 프롬프트 생성 → 📋 복사 버튼

[VPS — FastAPI 백엔드]
  POST /api/feedback         ← 피드백 수집
  GET  /api/feedback/summary ← 미반영 피드백 요약
  POST /api/chat             ← 단순 Q&A (FTS5 검색, Haiku 답변)
  POST /api/prompt           ← 심층 분석용 프롬프트 생성 (LLM 호출 없음)
  POST /api/briefings/ingest ← 브리핑 JSON 인덱싱
  
  [데이터]
  feedback.db (SQLite)       ← 피드백 누적
  briefings.db (SQLite FTS5) ← 브리핑 아카이브 인덱싱

[GitHub Actions — daily-briefing 파이프라인]
  ① GET /api/feedback/summary → 미반영 피드백 조회
  ② apply-feedback → stable_profile.json 가중치 조정 (10% 범위 제한)
  ③ collect → brief → deploy → push
  ④ POST /api/briefings/ingest → 당일 브리핑 인덱싱
```

---

## 기능 1 상세: 피드백 시스템

### 피드백 수집 체계

| 유형 | 행동 | 가중치 | 구현 |
|------|------|--------|------|
| 명시적 | 👍 클릭 | +0.05 | 버튼 + fetch |
| 명시적 | 👎 클릭 | -0.05 | 버튼 + fetch |
| 명시적 | 카테고리 "더 보기" | +0.03 | 버튼 + fetch |
| 암묵적 1순위 | 소스 링크 클릭 | +0.02 | JS event listener |
| 암묵적 2순위 | 카드 펼쳐서 읽음 | +0.01 | JS expand 이벤트 |

### 반영 규칙

- 매일 brief 실행 전 자동 반영
- 전체 가중치의 10% 이내로 제한
- 단일 피드백 영향: ±0.05 (score 3 기준 ±1.7%)

### API 스키마

```
POST /api/feedback
{
  "date": "2026-02-23",
  "article_id": "25aae26fadbb",
  "type": "explicit",       // "explicit" | "implicit"
  "action": "thumbs_up",    // "thumbs_up" | "thumbs_down" | "category_more" | "expand" | "link_click"
  "category": "fab_capex",  // 카테고리 조정 시
  "timestamp": "2026-02-23T07:30:00+09:00"
}

Response: {"status": "ok"}
```

### 프로필 조정 로직

```python
# profiler/feedback_adjuster.py
def apply_feedback(profile: dict, feedbacks: list[dict]) -> dict:
    """피드백을 프로필에 반영한다. 전체 가중치 10% 이내 제한."""
    category_scores = {}
    for fb in feedbacks:
        cat = fb.get("category") or _article_to_category(fb["article_id"])
        weight = WEIGHT_MAP[fb["action"]]  # +0.05, -0.05, etc.
        category_scores[cat] = category_scores.get(cat, 0) + weight
    
    for item in profile["top_priorities"]:
        cat = item["name"]
        if cat in category_scores:
            delta = category_scores[cat]
            max_delta = item["score"] * 0.10  # 10% 제한
            clamped = max(-max_delta, min(max_delta, delta))
            item["score"] = round(item["score"] + clamped, 2)
    
    return profile
```

### 구현할 파일

| 파일 | 역할 |
|------|------|
| `backend/main.py` | FastAPI 앱 |
| `backend/models.py` | Pydantic 모델 |
| `backend/db.py` | SQLite 연결 |
| `backend/feedback_api.py` | POST /api/feedback, GET /api/feedback/summary |
| `src/profiler/feedback_adjuster.py` | 피드백 → 프로필 조정 |
| `src/briefer/html_renderer.py` | 👍/👎 버튼 + JS fetch 추가 |
| `src/main.py` | `apply-feedback` CLI 명령 추가 |
| `.github/workflows/daily-briefing.yml` | feedback 반영 + ingest 단계 추가 |

---

## 기능 2 상세: 검색 + 프롬프트 생성기

### 2단 구조

**1단: 단순 Q&A (VPS 자체 처리)**

```
💬 "지난주 반도체 뉴스 뭐 있었어?"
→ FTS5 검색 → 관련 기사 목록 반환 (LLM 호출 없음 또는 Haiku 경량 요약)
```

**2단: 심층 분석 (프롬프트 생성 → 외부 LLM)**

```
💬 "반도체 투자 동향이 SK에코플랜트에 미치는 영향 분석해줘"
→ FTS5 검색 → 관련 기사 5~10건 추출
→ 프로필 + 기사 컨텍스트 + 질문 조합 → 프롬프트 생성
→ "📋 프롬프트 복사" 버튼 → 클립보드
→ 아버지가 ChatGPT에 붙여넣기
```

### 프롬프트 생성 템플릿

```
당신은 건설/반도체/데이터센터 업계 임원 자문역입니다.

## 독자 프로필
- 핵심 관심사: {top_priorities에서 상위 10개}
- SK에코플랜트 렌즈: {sk_ecoplant_lens}

## 관련 기사 ({날짜 범위})
{검색된 기사 3~10건, 각각 날짜/헤드라인/Fact/Impact}

## 질문
{사용자 질의}

위 기사들을 근거로 답변해주세요. 출처를 명시하고, 확인되지 않은 내용은 "미확인"으로 표시하세요.
```

### API 스키마

```
POST /api/chat
{
  "query": "지난주 반도체 뉴스",
  "date_from": "2026-02-16",  // 선택
  "date_to": "2026-02-23"     // 선택
}

Response:
{
  "type": "direct",  // "direct" | "prompt"
  "articles": [...],
  "answer": "지난주 반도체 관련 주요 뉴스 3건입니다: ..."
}

POST /api/prompt
{
  "query": "반도체 투자 동향이 SK에코플랜트에 미치는 영향",
  "date_from": "2026-02-16"
}

Response:
{
  "prompt": "당신은 건설/반도체/... (전체 프롬프트 텍스트)",
  "articles_used": 7,
  "date_range": "2026-02-16 ~ 2026-02-23"
}
```

### briefings.db 스키마

```sql
CREATE TABLE briefings (
  date TEXT PRIMARY KEY,
  json_data TEXT,
  ingested_at TEXT
);

CREATE VIRTUAL TABLE briefings_fts USING fts5(
  date, headlines, facts, categories,
  content=briefings, content_rowid=rowid
);
```

### GPT 프로젝트 연동

아버지가 ChatGPT에 "News Agent 분석" 프로젝트를 만들고:
- `stable_profile.json`을 파일로 업로드 (고정 컨텍스트)
- 생성된 프롬프트를 붙여넣으면 프로필을 이미 알고 있으므로 더 정확한 답변

### 구현할 파일

| 파일 | 역할 |
|------|------|
| `backend/chat_api.py` | POST /api/chat (FTS5 검색 + Haiku 답변) |
| `backend/prompt_api.py` | POST /api/prompt (프롬프트 생성) |
| `backend/ingest_api.py` | POST /api/briefings/ingest |
| `backend/db.py` | briefings.db + FTS5 |
| `src/briefer/html_renderer.py` | 챗 UI (플로팅 버튼 + 패널) |
| `src/deployer/nav_injector.py` | 챗 UI JS 주입 |

---

## 보안

| 항목 | 대응 |
|------|------|
| VPS API 인증 | Bearer 토큰 1개 (환경변수) — 한 명만 사용 |
| HTTPS | Let's Encrypt (필수) |
| ANTHROPIC_API_KEY | VPS 환경변수, 1단(Haiku) 에서만 사용. 2단(프롬프트 생성)은 API 키 불필요 |
| 브리핑 데이터 | SQLite 파일 권한 600, VPS 방화벽 |
| SSH | 키 인증만, 패스워드 비활성화 |
| CORS | GitHub Pages 도메인만 허용 |

---

## 구현 순서

1. VPS에 FastAPI 서버 셋업 (`backend/`)
2. 피드백 API (POST /api/feedback) + DB
3. 브리핑 HTML에 👍/👎 버튼 + 암묵적 피드백 JS
4. `apply-feedback` CLI + 파이프라인 연동
5. briefings.db 인덱싱 (POST /api/briefings/ingest)
6. 검색 API (POST /api/chat)
7. 프롬프트 생성 API (POST /api/prompt)
8. 챗 UI (플로팅 버튼 + 패널)
9. 보안 (HTTPS + Bearer + CORS)

---

## 참조 파일

| 파일 | 용도 |
|------|------|
| `output/stable_profile.json` | 현재 프로필 (피드백 조정 대상) |
| `output/briefings/*.json` | 브리핑 데이터 (인덱싱 대상) |
| `src/briefer/html_renderer.py` | 버튼/JS 추가 대상 |
| `src/main.py` | CLI 명령 추가 |
| `.github/workflows/daily-briefing.yml` | 파이프라인 연동 |
| `docs/IMPROVEMENT-BACKLOG.md` | 과제 백로그 |

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- VPS 코드는 `backend/` 디렉토리에 분리
- 기존 테스트 통과 유지
- 보안: API 키/토큰을 코드에 하드코딩하지 않을 것
- 피드백 가중치 조정은 10% 이내 제한 (편향 방지)
