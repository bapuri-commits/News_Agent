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

### 2. 사용자 피드백 기능

**우선순위**: 낮음
**관련 파일**: `src/briefer/html_renderer.py`, `src/deployer/index_generator.py`, 신규 `src/profiler/feedback_adjuster.py`

**핵심 제약**: 서버 없음 (GitHub Pages 정적 사이트).

**방안**: LocalStorage + 수동 export (아버지가 한 기기에서만 사용하므로 충분)

```
[브리핑 웹 페이지]
  Top5 카드에 👍/👎 버튼 + 카테고리 "더 보기"/"줄이기" 버튼
      ↓ (클릭 시)
  localStorage 저장
  {"2026-02-23": {"thumbs": {"id": "up"}, "category_adjust": {"fab_capex": +1}}}
      ↓ (인덱스에 "피드백 내보내기" 버튼)
  feedback.json 다운로드
      ↓ (CLI로 수동 반영)
  stable_profile.json 가중치 미세 조정
```

**구현 단계**:
1. Top5 카드에 👍/👎 버튼 삽입 (`html_renderer.py`)
2. JS: 클릭 → localStorage 저장 + 시각적 피드백 (`html_renderer.py`)
3. 인덱스에 "피드백 내보내기" 버튼 (`index_generator.py`)
4. (선택) `apply-feedback` CLI 명령 (`main.py`, `profiler/feedback_adjuster.py`)

**향후 자동 반영 경로**: GitHub Actions `workflow_dispatch` input으로 피드백 전달 → 파이프라인이 프로필 가중치 조정 → 다음 날 수집 반영.

**예상 공수**: 6~8시간

---

### 3. 과거 브리핑 검색

**우선순위**: 낮음
**관련 파일**: `src/deployer/site_builder.py`, `src/deployer/index_generator.py`

**핵심 제약**: 서버 없음. 클라이언트 사이드 JS 키워드 검색으로 MVP 구현.

**방안**: 빌드 시 `web/search-index.json` 생성 → 인덱스 페이지에서 fetch 후 키워드 매칭

```
[site_builder.py 빌드 시]
  briefings/*.json에서 검색용 필드만 추출
      ↓
  web/search-index.json 생성
  {
    "2026-02-23": {
      "top5": [{"headline": "...", "category": "fab_capex", "fact": "..."}],
      "categories": ["fab_capex", "dc_power"],
      "sk_headline": "..."
    }
  }

[인덱스 페이지 검색 UI]
  🔍 "반도체 수주" 입력
      ↓
  JS: search-index.json fetch → 키워드 매칭 → 결과 카드 표시
```

**구현 단계**:
1. `search-index.json` 생성 로직 (`site_builder.py`)
2. 인덱스 페이지에 검색 입력 UI + JS (`index_generator.py`)
3. JS: fetch → 키워드 매칭 → 결과 표시 (`index_generator.py`)
4. (향후) LLM RAG: Vercel Function으로 자연어 질의 응답

**예상 공수**: 8~12시간 (MVP 키워드 검색은 4~5시간)

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
