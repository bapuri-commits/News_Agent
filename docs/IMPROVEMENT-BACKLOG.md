# News_Agent 향후 개선 과제 백로그

> 최종 업데이트: 2026-02-23
> 완료된 과제는 하단에 이력으로 보존.

---

## 미해결 과제

### 1. 텍스트 버전 근본 재설계

**우선순위**: 중간 (보류)
**관련 파일**: `src/briefer/markdown_renderer.py`, `src/briefer/briefing_generator.py`, 파이프라인 전반

**현상**: 현재 텍스트(MD) 버전은 LLM이 요약한 결과를 다시 텍스트로 렌더링하는 구조. HTML 카드 버전의 내용을 그대로 텍스트로 옮긴 것이어서 독립적 가치가 부족.

**사용자 의도**: 선별된 원본 기사를 약간만 가공한 풍부한 레퍼런스. 주요 내용과 서브 내용이 모두 포함된 신뢰도 있는 자료.

**필요 변경**: 파이프라인 구조 변경 — 수집된 원본 기사 데이터를 텍스트 렌더러에 직접 전달하여, LLM 요약과 별개로 원본 기반 레퍼런스 문서 생성.

**예상 공수**: 4~6시간

---

### 2. 사용자 피드백 → 프로필 자동 반영

**우선순위**: 높음
**관련 파일**: `src/briefer/html_renderer.py`, 신규 `backend/` (VPS FastAPI)

**환경**: VPS 서버 보유. GitHub Pages(정적) + VPS(API) 하이브리드.

**아키텍처**:
```
[브리핑 웹 페이지]
  Top5 카드에 👍/👎 버튼 + 카테고리 "더 보기"/"줄이기" 버튼
      ↓ (클릭 시)
  fetch('https://vps.example/api/feedback', {articleId, vote, category_adjust})
      ↓
[VPS FastAPI]
  POST /api/feedback → feedback.db (SQLite) 누적
      ↓
[daily-briefing 파이프라인 (매일 자동)]
  brief 실행 전 → VPS에서 미반영 피드백 조회
  → stable_profile.json 가중치 미세 조정 (5~10% 범위 제한)
  → 조정된 프로필로 collect + brief 실행
  → 다음 날 브리핑에 자동 반영
```

**구현 단계**:
1. VPS에 FastAPI 서버 구축 (`backend/main.py`, `backend/models.py`)
2. POST /api/feedback 엔드포인트 + SQLite 저장
3. Top5 카드에 👍/👎 버튼 + JS fetch (`html_renderer.py`)
4. `apply-feedback` CLI 명령 (`src/main.py`, `src/profiler/feedback_adjuster.py`)
5. daily-briefing 워크플로우에 feedback 반영 단계 추가
6. 가중치 조정 범위 제한 (편향 방지)

**예상 공수**: 8~12시간

---

### 3. 기사 기반 Q&A 챗봇 (RAG)

**우선순위**: 높음
**관련 파일**: 신규 `backend/` (VPS FastAPI), `src/deployer/index_generator.py`

**환경**: VPS 서버 (피드백 API와 동일 서버에 통합).

**아키텍처**:
```
[매일 brief 완료 후]
  당일 브리핑 JSON → VPS POST /api/briefings/ingest
  → briefings.db (SQLite FTS5) 인덱싱
      ↓
[브리핑 웹 페이지 — 챗 UI]
  💬 "지난주 반도체 수주 관련 뉴스 정리해줘"
      ↓
  fetch('https://vps.example/api/chat', {query})
      ↓
[VPS FastAPI]
  POST /api/chat
    → briefings.db FTS5 검색 (키워드 + 날짜 필터)
    → 관련 기사 3~5건 추출
    → LLM (Haiku)에 컨텍스트로 전달
    → 답변 생성 (출처 포함)
    → 스트리밍 응답
```

**구현 단계**:
1. briefings.db 스키마 설계 + FTS5 인덱싱 (`backend/db.py`)
2. POST /api/briefings/ingest 엔드포인트
3. POST /api/chat 엔드포인트 (검색 → LLM 답변)
4. 브리핑 페이지에 챗 UI (플로팅 버튼 → 슬라이드 패널)
5. daily-briefing 워크플로우에 ingest 단계 추가
6. (향후) 스트리밍 응답 (SSE)

**비용**: Haiku $0.005/질의 (월 100회 사용 가정 $0.50)

**예상 공수**: 12~16시간

---

### 4. 프리셋 확장

**우선순위**: 낮음
**관련 파일**: `src/briefer/design_system.py`

8→12개 프리셋 확장, 계절/시즌 테마, 마이크로 애니메이션 (카드 등장, 숫자 카운트업).

**예상 공수**: 3~5시간

---

## 완료 이력

### ✅ 본문 크롤링 개선 (높음 → 완료)

googlenewsdecoder + HTTP redirect + Playwright headless browser 3단계 전략 구현.
크롤링 성공률 0% → 80% (4/5건). 지역 Google News 도메인 대응 포함.

### ✅ 카테고리별 요약 심화 (중간 → 완료)

Stage 3에 Impact 필드 추가. 3건 이상 카테고리에 impact 포함.

### ✅ 뉴스 수집 튜닝 (중간 → 완료)

- S7 내부 2차 dedup (제목+스니펫 Jaccard 0.45) — 보도자료 재작성 29건 추가 제거
- S7 dedup 순서 안정화 (발행시간+제목 정렬)
- 전문매체 스코어링 보너스 (S1/S2/S5 +0.15)
- S5 건설전문 RSS 피드 2개 추가 (Construction Dive, World Construction Today)
- 짧은 키워드 단어 경계 (`\b` + `re.ASCII`)
- dedup SOURCE_GROUP_RANK 전문매체 우선
- _ensure_source_minimum 교체 로직 (가득 찬 리스트 대응)
- 결과: 전문매체 비율 16%→23%, S7 비율 81%→77%

### ✅ HTML 테마 재설계 (낮음 → 완료)

8개 큐레이팅된 디자인 프리셋 × 3 레이아웃(hero/grid/editorial) × 4 카드 스타일.
콘텐츠 시그니처 기반 자동 선택, 최근 3일 중복 회피, LLM 비용 0.

### ✅ 카테고리 확장 (추가 과제 → 완료)

12→22개 카테고리 (INITIAL-SCOPE 16개 서브스코프 완전 반영).

### ✅ 소스 다양성 강화 (추가 과제 → 완료)

dedup 전문매체 우선, _ensure_source_minimum 교체 로직, S5 피드 추가.

### ✅ Design Lint Layer (추가 과제 → 완료)

Top5 Fact 500자 초과, 출처 누락, 빈 카테고리, 소스 편향 85% 초과 자동 경고.

### ✅ 날짜 검색 기능 (추가 과제 → 완료)

인덱스 페이지 달력 아이콘 버튼 + showPicker + JS 필터링.

### ✅ 한글 단어 경계 매칭 수정 (추가 과제 → 완료)

`re.ASCII` 플래그 적용으로 `"PF리스크"` 같은 공백 없는 한글 조합에서 단어 경계 정상 작동.
