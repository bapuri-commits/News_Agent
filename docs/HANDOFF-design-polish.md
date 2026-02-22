# 디자인 세련화 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 붙여넣으면 디자인 작업을 시작할 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Phase 7 MVP가 완료되어 GitHub Pages에 배포 중이다.

- 배포 URL: https://bapuri-commits.github.io/News_Agent/
- 현재 브리핑: `web/2026-02-22.html` (1건)

## 현재 상태: 다층 디자인 시스템 구현 완료

### 구현된 아키텍처 (3-Layer)

```
Layer 1: Core Information (절대 고정)
  └─ 브리핑 JSON 스키마 (top5, by_category, sk_ecoplant, risks, ...)

Layer 2: Design System (design_system.py)
  ├─ 8개 큐레이팅된 프리셋 (Theme + Layout + Component 묶음)
  ├─ 콘텐츠 시그니처 분석 (알고리즘, LLM 비용 0)
  ├─ 최근 3일 이력 기반 중복 회피
  └─ themes.py 래퍼로 하위 호환 유지

Layer 3: CSS Variant System (html_renderer.py)
  ├─ Layout Variants: hero / grid / editorial
  ├─ Card Styles: elevated / glass / flat / bordered
  ├─ Dark Theme 지원
  ├─ 숫자 자동 하이라이트 (조, 억, %, MW 등)
  └─ 프로 디테일 (hover, spacing, typography, rhythm)
```

### 8개 디자인 프리셋

| 프리셋 | 레이아웃 | 카드 스타일 | 다크 | 발동 조건 |
|--------|----------|-------------|------|-----------|
| `hero_bold` | hero | elevated | ✗ | urgency high, 중대 뉴스 |
| `noir_data` | hero | glass | ✓ | 수치 밀도 높을 때 |
| `journal_classic` | editorial | flat | ✗ | 혼합 콘텐츠 |
| `grid_tech` | grid | bordered | ✗ | 반도체/장비 |
| `warm_earth` | editorial | bordered | ✗ | Deal Flow / EPC |
| `risk_crimson` | hero | elevated | ✗ | 리스크 4개 이상 |
| `ocean_depth` | grid | glass | ✗ | 인프라/시장 |
| `dawn_gradient` | editorial | elevated | ✗ | SK 에코플랜트 중심 |

### 레이아웃 Variant 상세

- **Hero**: Top 1 카드가 대형 히어로로 표시 (원형 랭크 번호, 큰 제목). 나머지는 일반 크기.
- **Grid**: Top 5가 2열 그리드. Top 1은 full-width 스팬.
- **Editorial**: 좌측 정렬 헤더, 섹션 타이틀에 하단 보더, 카드는 보더 구분선 방식.

### 카드 스타일 Variant 상세

- **Elevated**: 강한 그림자 + 4px 왼쪽 보더. 존재감 있는 카드.
- **Glass**: 반투명 배경 + backdrop-filter blur. 다크 테마와 궁합 좋음.
- **Flat**: 그림자 없음, 1px 보더. 미니멀하고 깔끔.
- **Bordered**: 1px 보더 + 호버 시 미묘한 그림자. 클래식한 느낌.

---

## 파일 구조

| 파일 | 역할 | 변경 내역 |
|------|------|-----------|
| `src/briefer/design_system.py` | **신규** — 디자인 프리셋 + 시그니처 분석 + 선택 로직 |
| `src/briefer/themes.py` | 수정 — design_system의 호환 래퍼 |
| `src/briefer/html_renderer.py` | 대폭 수정 — CSS variant + 숫자 하이라이트 + 프로 디테일 |
| `src/briefer/constants.py` | 변경 없음 |
| `src/deployer/index_generator.py` | 변경 없음 (themes.py 래퍼로 호환) |
| `src/deployer/nav_injector.py` | 변경 없음 |
| `src/deployer/site_builder.py` | 변경 없음 |
| `output/design_history.json` | 자동 생성 — 프리셋 선택 이력 |

---

## 핵심 원칙

- **읽는 맛** — 임원이 매일 아침 폰으로 열어보고 싶은 퀄리티
- **정보 계층** — 중요한 것이 먼저 눈에 들어오는 시각적 위계
- **매일 다른 느낌** — 8개 프리셋 × 이력 회피로 연속 3일 같은 디자인 안 나옴
- **모바일 퍼스트** — 아버지가 폰으로 읽으므로 모바일에서 완벽해야 함
- **비용 0** — 디자인 선택에 LLM 호출 없음 (알고리즘만)

---

## 현재 HTML 구조

### 브리핑 페이지 (`html_renderer.py`에서 생성)

```html
<div class="container layout-{layout} cards-{card_style} [theme-dark]" data-preset="{preset_key}">
  <header class="header">  <!-- 로고, 날짜, 테마 배지, reading time -->
  <!-- nav bar (deployer가 주입) -->
  <section class="section section-top5">
    <div class="top5-grid">  <!-- Top 5 카드 (접이식) -->
  </section>
  <section class="sk-section"><!-- SK에코플랜트 렌즈 --></section>
  <section><!-- 카테고리별 동향 (접이식) --></section>
  <section><!-- 리스크 종합 --></section>
  <section><!-- Next Signals --></section>
  <section><!-- 소스 분포 (바 차트) + 총 건수 --></section>
  <footer><!-- 생성 시각 --></footer>
</div>
```

### 인덱스 페이지 (`index_generator.py`에서 생성)

```html
<div class="idx-container">
  <header class="idx-header">  <!-- 로고, 서브타이틀 -->
  <main class="idx-grid">
    <a class="idx-card">  <!-- 날짜별 카드 (최신순) -->
  </main>
  <footer class="idx-footer">
</div>
```

---

## 추가 기능: 텍스트 버전 (MD → HTML 변환 배포) — 미구현

### 배경

최종 산출물은 2가지로 설계되어 있다:
1. `YYYY-MM-DD.html` — 웹 UI 브리핑 (카드 기반)
2. `YYYY-MM-DD.md` — 텍스트 브리핑 (카톡/이메일용)

현재 MD 파일은 `output/briefings/`에만 있고 웹에서 접근할 수 없다.

### 구현 방향

1. **`site_builder.py` 수정** — MD 파일도 `web/`에 포함
2. **브리핑 HTML에 "텍스트 버전" 링크 추가**
3. **텍스트 버전 페이지 디자인** — 미니멀 + "전체 복사" 버튼
4. **인덱스 페이지에도 반영**

---

## 후속 개선 과제

### 1차: 인덱스/네비게이션 디자인 통합 (미착수)

인덱스 페이지(`_INDEX_CSS`)와 네비게이션 바(`_NAV_CSS`)는 아직 구 디자인.
브리핑 페이지와 시각적 일관성 맞추기:
- 인덱스 카드에 테마 배경 반영
- nav 바에 backdrop-filter 추가
- 테마 다크 모드 시 nav/인덱스도 대응

### 2차: Design Lint Layer (미착수)

디자인 품질을 자동으로 보장하는 검증 규칙:
- 카드 본문 5줄 초과 금지
- WCAG 대비비율 준수
- 숫자 3개 이상 시 KPI 스타일 자동 적용
- SourceGroup 배지 누락 금지

### 3차: 프리셋 확장

- 프리셋 8→12개 확장 (계절/시즌 테마 등)
- 더 세분화된 Component Variant (Risk 칩 스타일, 타임라인 컴포넌트 등)
- 마이크로 애니메이션 (카드 등장, 숫자 카운트업)

---

## 작업 흐름

1. `html_renderer.py`의 `_CSS` 수정 → `python -m src.main brief --date 2026-02-22`로 재생성
2. `python -m src.main deploy`로 `web/` 재생성
3. 브라우저에서 결과 확인 (특히 모바일 뷰)
4. 만족하면 `python -m src.main deploy --push`로 배포

**주의: `brief` 명령은 LLM API를 호출하므로 비용이 발생한다.** CSS만 수정할 때는 빠른 반복을 위해 `web/2026-02-22.html`을 직접 수정하며 확인한 뒤, 최종 결과를 `_CSS`에 반영하는 방식을 권장한다.

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `src/briefer/design_system.py` | 디자인 프리셋 + 선택 로직 (핵심) |
| `src/briefer/html_renderer.py` | 브리핑 HTML + CSS (수정 대상) |
| `src/briefer/themes.py` | 테마 호환 래퍼 (참조) |
| `src/briefer/constants.py` | 카테고리 라벨/색상 (참조) |
| `src/deployer/index_generator.py` | 인덱스 페이지 HTML + CSS (수정 대상) |
| `src/deployer/nav_injector.py` | 네비게이션 바 CSS (수정 대상) |
| `web/2026-02-22.html` | 현재 배포된 브리핑 (비교용) |
| `web/index.html` | 현재 배포된 인덱스 (비교용) |
| `output/briefings/2026-02-22.json` | 브리핑 데이터 (테스트용) |
| `output/design_history.json` | 프리셋 선택 이력 (자동 생성) |

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- CSS는 인라인으로 유지 (별도 파일 만들지 않음)
- 모바일 반응형 필수 (600px, 480px 브레이크포인트)
- 기존 HTML 구조(태그, 클래스명)를 최대한 유지 — CSS로 해결
- 기존 테스트 108개 통과 유지
- 접이식 카드의 JS 동작을 깨뜨리지 않을 것
- 브라우저에서 실제 확인 후 수정
