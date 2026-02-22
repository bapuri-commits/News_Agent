# Phase 7 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 7 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Phase 1~6 완료. Phase 7에서 **웹에 올려서 실제로 볼 수 있게** 만든다.

**최종 산출물 2가지:**
1. `output/briefings/YYYY-MM-DD.md` — 텍스트 브리핑 (카톡/이메일용)
2. `output/briefings/YYYY-MM-DD.html` — 웹 UI 브리핑 (Google Opal 스타일, 카드 기반)

---

## Phase 1~6 완료 상태

```
Program #1: 프로필 추출 ━━━━━━━━━━━━━ 완료
  Phase 1: ZIP 파싱 (65개 대화, 643개 메시지)
  Phase 2: PII 마스킹 + 청킹 (73개 chunk)
  Phase 3: Claude Opus micro-summary (28개 비즈니스)
  Phase 4: Stable Profile 확정 (26개 우선순위)

Program #2: 뉴스 파이프라인 ━━━━━━━━━ 완료
  Phase 5: News Collector (GNews RSS + 14개 전문매체 RSS)
  Phase 6: Briefing Generator (4단계 LLM, Sonnet+Opus 믹스)
    → output/briefings/YYYY-MM-DD.json, .md, .html 생성
```

---

## Phase 7: 웹 배포 — 해야 할 작업

### 목표

Phase 6에서 생성되는 `YYYY-MM-DD.html` 브리핑을 **웹에서 접근 가능**하게 배포.
아버지가 매일 아침 브라우저/폰으로 열어서 브리핑을 읽을 수 있어야 한다.

### 요구사항

1. **인덱스 페이지** — 날짜 목록이 나열되고, 클릭하면 해당 날짜 브리핑으로 이동
2. **날짜 네비게이션** — 각 브리핑 페이지 내에서 이전/다음 날짜로 이동
3. **모바일 반응형** — 기존 HTML은 이미 반응형이므로, 인덱스/네비게이션만 추가
4. **정적 배포** — GitHub Pages 또는 Vercel (서버 불필요)
5. **자동화 연결** — `brief` 커맨드 실행 시 웹용 파일도 함께 생성/배포

### 배포 아키텍처

```
[매일 실행]
python -m src.main collect --date YYYY-MM-DD
python -m src.main brief --date YYYY-MM-DD
python -m src.main deploy   ← Phase 7에서 추가

[deploy가 하는 일]
output/briefings/
  ├─ 2026-02-22.html
  ├─ 2026-02-23.html
  └─ ...
    ↓ 복사 + 인덱스 생성
web/
  ├─ index.html             ← 날짜 목록 인덱스 (자동 생성)
  ├─ 2026-02-22.html        ← 날짜 네비게이션 주입된 버전
  ├─ 2026-02-23.html
  └─ style.css              ← (선택) 공유 스타일시트
    ↓ git push
GitHub Pages에서 서빙
```

### 구현할 파일

#### 1. `src/deployer/__init__.py` — 빈 파일

#### 2. `src/deployer/site_builder.py` — 정적 사이트 빌더

```python
def build_site(briefings_dir: Path, output_dir: Path) -> None:
    """briefings/ 폴더의 HTML 파일들을 web/ 폴더로 복사하면서
    인덱스 페이지를 생성하고, 각 브리핑에 날짜 네비게이션을 주입한다.
    
    1. briefings/*.html 스캔 → 날짜 목록 추출 (정렬)
    2. 각 HTML에 이전/다음 날짜 네비게이션 바 주입
    3. index.html 생성 (날짜 목록 카드)
    4. web/ 폴더에 출력
    """
```

#### 3. `src/deployer/nav_injector.py` — 네비게이션 바 주입

```python
def inject_nav(html_content: str, prev_date: str | None, next_date: str | None, 
               current_date: str) -> str:
    """기존 HTML의 <header> 아래에 날짜 네비게이션 바를 삽입한다.
    
    ← 2026-02-21  |  2026-02-22  |  2026-02-23 →
    """
```

#### 4. `src/deployer/index_generator.py` — 인덱스 페이지 생성

```python
def generate_index(dates: list[str], output_path: Path) -> None:
    """날짜 목록으로 인덱스 페이지를 생성한다.
    
    - 날짜별 카드 (최신순)
    - 각 카드 클릭 시 해당 날짜 브리핑으로 이동
    - Google Opal 스타일 유지
    - 모바일 반응형
    """
```

#### 5. `main.py`에 `deploy` 서브커맨드 추가

```
python -m src.main deploy [--output-dir web/]
```

1. `output/briefings/*.html` 스캔
2. `build_site()` 호출 → `web/` 폴더 생성
3. (선택) `git add web/ && git commit && git push` 자동화

### 인덱스 페이지 디자인 (Google Opal 스타일)

```
┌─────────────────────────────────────┐
│  Executive Briefing Archive         │
│  건설 · 반도체 · 데이터센터 · 인프라    │
├─────────────────────────────────────┤
│                                     │
│  ┌─────────────────────────────┐    │
│  │ 2026-02-23  Tech Focus      │    │
│  │ Top: TSMC 3nm 증설 발표     │    │
│  │ SK에코: IPO 재추진 신호      │    │
│  └─────────────────────────────┘    │
│                                     │
│  ┌─────────────────────────────┐    │
│  │ 2026-02-22  SK Focus        │    │
│  │ Top: SK에코플랜트 IPO 전환   │    │
│  │ 삼성 유보금 163조 역대 최대   │    │
│  └─────────────────────────────┘    │
│                                     │
└─────────────────────────────────────┘
```

각 카드에 표시할 정보 (briefing JSON에서 추출):
- 날짜
- 테마 라벨 (Tech Focus / SK Focus 등)
- Top 1 헤드라인
- SK에코플랜트 헤드라인 (있으면)

### 날짜 네비게이션 바 디자인

```
┌──────────────────────────────────────┐
│  ← 2026-02-21  │  📅 2026-02-22  │  2026-02-23 →  │  🏠 목록  │
└──────────────────────────────────────┘
```

- `<header>` 바로 아래에 삽입
- sticky로 스크롤해도 상단 고정
- 이전/다음 날짜가 없으면 비활성 처리

---

## 현재 HTML 구조 (Phase 6에서 생성)

각 `YYYY-MM-DD.html`은 **CSS/JS 인라인 포함된 단일 파일**이다. 구조:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <style>/* 전체 CSS 인라인 */</style>
  <style>/* 테마 CSS 변수 오버라이드 */</style>
</head>
<body>
  <div class="container">
    <header class="header" style="background: {gradient}; ...">
      <!-- 로고, 날짜, 테마 배지 -->
    </header>
    <section><!-- Top 5 카드 --></section>
    <section><!-- SK에코플랜트 렌즈 --></section>
    <section><!-- 카테고리별 동향 --></section>
    <section><!-- 리스크 --></section>
    <section><!-- Next Signals --></section>
    <section><!-- 소스 분포 --></section>
    <footer><!-- 생성 시각 --></footer>
  </div>
  <script>/* 카드 접이식 JS */</script>
</body>
</html>
```

네비게이션 주입 시 `</header>` 바로 뒤에 nav 바를 삽입하면 된다.

---

## 브리핑 JSON 스키마 (인덱스 카드용 참조)

```json
{
  "date": "2026-02-22",
  "generated_at": "2026-02-21T16:59:56Z",
  "reading_time_min": 15,
  "top5": [
    {"headline": "SK에코플랜트, IPO 전략 전환해 FI와 협상", "category": "ipo", ...}
  ],
  "sk_ecoplant": {"headline": "SK에코플랜트, AI·반도체 중심 체질 개선 가속화", ...},
  "by_category": {"fab_capex": {...}, "dc_build": {...}, ...},
  "source_diversity": {"S6": 1, "S7": 30},
  "metadata": {"total_articles": 31, ...}
}
```

인덱스 카드에서 `top5[0].headline`, `sk_ecoplant.headline`, 테마 라벨을 추출해서 표시.

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `output/briefings/*.html` | Phase 6 산출물 (웹 UI 브리핑) |
| `output/briefings/*.json` | 구조화된 브리핑 데이터 (인덱스 카드 정보 추출용) |
| `src/briefer/html_renderer.py` | 기존 HTML 렌더러 (스타일 참고) |
| `src/briefer/constants.py` | 카테고리 라벨/색상 (인덱스에서 재사용) |
| `src/config.py` | 경로 상수 (`BRIEFINGS_DIR`, `OUTPUT_DIR`) |
| `docs/HANDOFF-phase7-plan.md` | Phase 7~9 전체 계획 + 향후 개선 과제 |

---

## 코드 구조 (현재 + Phase 7 추가분)

```
src/
  main.py                     # + deploy 서브커맨드 추가
  config.py                   # + WEB_DIR 경로 추가
  deployer/                   # Phase 7 (구현 필요)
    __init__.py
    site_builder.py            # 정적 사이트 빌드 오케스트레이터
    nav_injector.py            # HTML에 날짜 네비게이션 주입
    index_generator.py         # 인덱스 페이지 생성
  briefer/                    # Phase 6 (완료)
  collector/                  # Phase 5 (완료)
  ...

web/                          # Phase 7 출력 (정적 사이트)
  index.html
  2026-02-22.html
  2026-02-23.html
  ...
```

---

## GitHub Pages 배포 방법

1. `web/` 폴더를 레포 루트에 생성
2. GitHub 레포 Settings → Pages → Source: "Deploy from a branch" → Branch: main, Folder: /web
3. 또는 `gh-pages` 브랜치 사용

### 자동 배포 (선택)

`deploy` 커맨드에 `--push` 옵션을 추가하면:
```bash
python -m src.main deploy --push
```
→ `web/` 빌드 → `git add web/` → `git commit` → `git push`

---

## 구현 순서 권장

1. `config.py`에 `WEB_DIR` 경로 추가
2. `nav_injector.py` — 네비게이션 바 주입
3. `index_generator.py` — 인덱스 페이지 생성
4. `site_builder.py` — 전체 빌드 오케스트레이션
5. `main.py`에 `deploy` 서브커맨드
6. 로컬 테스트 (브라우저에서 확인)
7. GitHub Pages 배포 설정
8. 테스트 작성

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- 기존 HTML 스타일(Google Opal)과 일관성 유지
- 인덱스 페이지도 모바일 반응형 필수
- 정적 파일만 사용 (서버 불필요)
- 네비게이션 주입 시 기존 HTML 구조를 깨뜨리지 않을 것
- `output/` 폴더는 .gitignore에 포함됨 → `web/` 폴더는 별도로 git 추적 대상
