# Phase 8 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 8 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Phase 1~7 완료. Phase 8에서 **매일 자동 실행**되게 만든다.

**현재 수동 워크플로우 (매일 3줄 실행):**
```bash
python -m src.main collect --date YYYY-MM-DD   # 뉴스 수집 (GNews + RSS)
python -m src.main brief --date YYYY-MM-DD     # 브리핑 생성 (LLM 4단계)
python -m src.main deploy --push               # 웹 빌드 + git push → Pages 자동 배포
```

**Phase 8 목표:** 위 과정을 GitHub Actions 스케줄로 자동화하여, 매일 아침 아버지가 폰으로 새 브리핑을 열 수 있게 한다.

---

## Phase 1~7 완료 상태

```
Program #1: 프로필 추출 ━━━━━━━━━━━━━ 완료
  Phase 1: ZIP 파싱 (65개 대화, 643개 메시지)
  Phase 2: PII 마스킹 + 청킹 (73개 chunk)
  Phase 3: Claude Opus micro-summary (28개 비즈니스)
  Phase 4: Stable Profile 확정 (26개 우선순위)

Program #2: 뉴스 파이프라인 ━━━━━━━━━ 완료
  Phase 5: News Collector (GNews RSS + 14개 전문매체 RSS)
  Phase 6: Briefing Generator (4단계 LLM, Sonnet+Opus 믹스)

Program #3: 배포 ━━━━━━━━━━━━━━━━━━━ 완료
  Phase 7: 정적 사이트 빌더 + GitHub Pages 배포
    → https://bapuri-commits.github.io/News_Agent/
```

---

## Phase 8 선행 수정 — 완료

Phase 8 구현 전에 발견된 문제를 먼저 해결했다.

### 1. `.gitignore` 패턴 수정 (CRITICAL)

**문제:** `output/`(디렉토리 자체 무시)로는 부정 패턴 `!output/stable_profile.json`이 작동하지 않음. Git 규칙상 부모 디렉토리가 무시되면 내부 파일의 부정 규칙은 무효.

**수정:** `output/` → `output/*`(내용물 무시)로 변경하여 부정 패턴이 정상 작동하도록 함.

```gitignore
# Project output (generated data, not source)
output/*
!output/stable_profile.json
```

### 2. `site_builder.py` CI 호환 수정 (CRITICAL)

**문제:** 기존 `build_site()`가 `web/` 기존 HTML을 전부 삭제한 뒤 `output/briefings/`만 스캔. CI에서는 당일 브리핑만 존재하므로 과거 브리핑이 모두 삭제됨.

**수정:**
- `web/` 기존 파일을 삭제하지 않고 새 브리핑만 추가/덮어쓰기
- 전체 날짜 목록은 `web/` 디렉토리 기준으로 추출
- 기존 파일의 nav도 새 날짜 추가 시 갱신 (이전/다음 링크 업데이트)
- `nav_injector.py`에 `strip_nav()` 함수 추가하여 중복 nav 방지

### 3. `nav_injector.py`에 `strip_nav()` 추가

기존 HTML에 이미 주입된 nav를 제거하는 함수 추가. `build_site()`가 매 빌드마다 모든 파일의 nav를 갱신할 때 중복 방지.

---

## Phase 8: 자동 스케줄링 — 해야 할 작업

### 목표

매일 KST 06:00 (UTC 21:00 전날)에 자동으로 `collect → brief → deploy` 파이프라인을 실행하여 새 브리핑을 웹에 배포한다.

### 핵심 문제: `output/` 폴더가 `.gitignore`에 포함됨

현재 `output/*`가 gitignore 대상이다 (단, `stable_profile.json` 예외). CI에서 파이프라인을 실행하려면 다음 파일이 반드시 필요하다:

| 파일 | 용도 | 해결 방법 |
|------|------|-----------|
| `output/stable_profile.json` | 프로필 (collect/brief의 필수 입력) | **레포에 커밋** — `.gitignore`에 예외 추가 ✅ 완료 |
| `output/rss_state.json` | RSS 중복 방지 상태 | CI에서는 매번 새로 시작해도 무방 (중복은 dedup이 처리) |
| `output/briefings/*.html` | 이전 브리핑들 | `web/`에 이미 있으므로 CI에서 재생성 불필요 — 당일분만 생성 |
| `output/collected/*.json` | 수집 원본 | CI에서 매번 새로 수집 |

### 구현할 파일

#### 1. `.github/workflows/daily-briefing.yml` — 일일 브리핑 자동화

**참고:** GITHUB_TOKEN으로 수행한 push는 다른 워크플로우를 트리거하지 않으므로, 기존 `deploy-pages.yml`과 충돌하지 않는다. `daily-briefing.yml` 안에 Pages 배포 job을 직접 포함해야 한다.

```yaml
name: Daily Briefing

on:
  schedule:
    # 매일 KST 06:00 = UTC 21:00 (전날)
    - cron: '0 21 * * *'
  workflow_dispatch:
    inputs:
      date:
        description: '브리핑 날짜 (YYYY-MM-DD, 비우면 오늘)'
        required: false

permissions:
  contents: write    # git push를 위해
  pages: write       # Pages 배포를 위해
  id-token: write    # Pages 인증

concurrency:
  group: daily-briefing
  cancel-in-progress: false

jobs:
  briefing:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: pip

      - name: Install dependencies
        run: pip install -r requirements.txt

      - name: Determine target date
        id: date
        run: |
          if [ -n "${{ github.event.inputs.date }}" ]; then
            echo "target=${{ github.event.inputs.date }}" >> $GITHUB_OUTPUT
          else
            # KST = UTC+9, 스케줄은 UTC 21:00에 실행 → KST 다음날 06:00
            echo "target=$(TZ=Asia/Seoul date +%Y-%m-%d)" >> $GITHUB_OUTPUT
          fi

      - name: Collect news
        run: python -m src.main collect --date ${{ steps.date.outputs.target }}

      - name: Generate briefing
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: python -m src.main brief --date ${{ steps.date.outputs.target }}

      - name: Build static site
        run: python -m src.main deploy

      - name: Commit and push web/
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add web/
          git diff --staged --quiet || git commit -m "briefing: ${{ steps.date.outputs.target }}"
          git push

  deploy-pages:
    needs: briefing
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
      - uses: actions/configure-pages@v5
      - uses: actions/upload-pages-artifact@v3
        with:
          path: web
      - id: deployment
        uses: actions/deploy-pages@v4
```

**기존 YAML과 달라진 점:**
- `concurrency` 그룹 추가 — `workflow_dispatch` 연타 방지
- `Ensure output dirs` 단계 제거 — `main.py`의 `setup_logging()`에서 이미 호출
- `collect` 단계에서 불필요한 `ANTHROPIC_API_KEY` 제거 — collect는 GNews/RSS만 사용
- `brief` 단계에만 `ANTHROPIC_API_KEY` 설정

#### 2. `.gitignore` 수정 — stable_profile 예외 ✅ 완료

```gitignore
output/*
!output/stable_profile.json
```

#### 3. `site_builder.py` CI 호환 수정 ✅ 완료

- `web/` 기존 파일 보존 (삭제하지 않음)
- 전체 날짜 목록을 `web/` 기준으로 추출
- 모든 파일에 nav 갱신 (strip_nav → inject_nav)

#### 4. GitHub Secrets 설정 (수동)

레포 Settings → Secrets and variables → Actions → New repository secret:
- Name: `ANTHROPIC_API_KEY`
- Value: `.env` 파일의 ANTHROPIC_API_KEY 값

### 실행 시나리오

```
매일 UTC 21:00 (KST 06:00)
    ↓
GitHub Actions 트리거
    ↓
① collect: GNews + RSS → output/collected/YYYY-MM-DD.json
    ↓
② brief: LLM 4단계 → output/briefings/YYYY-MM-DD.{json,md,html}
    ↓
③ deploy: 새 HTML을 web/에 추가 + 전체 nav/인덱스 갱신 (기존 파일 보존)
    ↓
④ git commit + push (web/ 변경분만)
    ↓
⑤ deploy-pages job: GitHub Pages 배포
    ↓
아버지가 폰으로 https://bapuri-commits.github.io/News_Agent/ 접속
```

### 실패 처리

현재는 GitHub Actions 자체의 실패 알림(이메일)에 의존한다. Phase 9에서 텔레그램 봇 알림을 추가하면 `failure()` 시 텔레그램으로 알림을 보낼 수 있다.

### 비용 예상

| 항목 | 단가 | 일일 | 월간 |
|------|------|------|------|
| Anthropic API (Sonnet + Opus) | ~$0.50~1.00/회 | $0.50~1.00 | $15~30 |
| GitHub Actions | 무료 (public 레포, 월 2,000분) | ~3분 | ~90분 |
| **합계** | | | **$15~30/월** |

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `src/main.py` | CLI 진입점 (collect, brief, deploy 서브커맨드) |
| `src/config.py` | 경로 상수 + `ensure_output_dirs()` |
| `src/collector/` | Phase 5 뉴스 수집 |
| `src/briefer/` | Phase 6 브리핑 생성 |
| `src/deployer/site_builder.py` | Phase 7 정적 사이트 빌드 (CI 호환 수정됨) |
| `src/deployer/nav_injector.py` | nav 주입/제거 (`strip_nav` 추가됨) |
| `src/deployer/index_generator.py` | 인덱스 페이지 생성 |
| `.github/workflows/deploy-pages.yml` | 기존 Pages 배포 워크플로우 (수동/push 트리거) |
| `output/stable_profile.json` | 프로필 (collect/brief 필수 입력, gitignore 예외) |
| `.env` | ANTHROPIC_API_KEY (로컬용, gitignore 대상) |

---

## 코드 구조 (현재 + Phase 8 추가분)

```
.github/
  workflows/
    deploy-pages.yml          # Phase 7 (기존 — 수동/push 트리거, 변경 불필요)
    daily-briefing.yml        # Phase 8 (신규) — 일일 자동 파이프라인 + Pages 배포

src/
  main.py                     # collect, brief, deploy 서브커맨드 (변경 없음)
  config.py                   # 경로 상수 (변경 없음)
  collector/                  # Phase 5
  briefer/                    # Phase 6
  deployer/
    site_builder.py            # Phase 7 (수정됨 — CI 호환, 기존 파일 보존)
    nav_injector.py            # Phase 7 (수정됨 — strip_nav 추가)
    index_generator.py         # Phase 7 (변경 없음)

output/
  stable_profile.json         # .gitignore 예외로 커밋 필요
```

---

## 구현 순서

1. ✅ `.gitignore` 수정 — `output/*` + `!output/stable_profile.json`
2. ✅ `site_builder.py` 수정 — CI 호환 (기존 파일 보존)
3. ✅ `nav_injector.py` 수정 — `strip_nav()` 추가
4. `output/stable_profile.json` 커밋
5. `.github/workflows/daily-briefing.yml` 작성
6. GitHub Secrets에 `ANTHROPIC_API_KEY` 등록 (수동)
7. `workflow_dispatch`로 수동 테스트 실행
8. 스케줄 실행 확인 (다음 날 KST 06:00)

---

## 알려진 제한 사항

### 과거 브리핑 인덱스 카드 메타 정보

`index_generator.py`는 각 날짜의 JSON 파일(`output/briefings/{date}.json`)에서 테마, 헤드라인, SK에코 정보를 읽어 인덱스 카드를 생성한다. CI에서는 당일 JSON만 존재하므로, 과거 날짜의 인덱스 카드에는 메타 정보(테마 라벨, 헤드라인) 없이 날짜만 표시된다.

- 과거 브리핑 HTML 자체는 완전히 보존됨 (클릭하면 전체 내용 확인 가능)
- 로컬에서 `deploy`를 실행하면 과거 JSON도 있으므로 풍부한 카드 표시
- Phase 9에서 필요 시 메타 캐시 파일(`web/meta.json`)을 도입하여 해결 가능

---

## 의사결정 완료

### deploy-pages.yml 처리 → 병행 유지

- `daily-briefing.yml` 안에 Pages 배포 job 포함 (CI 자동화용)
- 기존 `deploy-pages.yml`은 그대로 유지 (수동 배포/로컬 push 시 자동 배포용)
- GITHUB_TOKEN push는 다른 워크플로우를 트리거하지 않으므로 충돌 없음

### 과거 브리핑 보존 → site_builder.py 수정으로 해결

- `web/` 기존 파일을 삭제하지 않고 새 브리핑만 추가/덮어쓰기
- 전체 날짜 목록은 `web/` 디렉토리 기준으로 추출

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- GitHub Actions YAML은 정확한 들여쓰기 (2칸 space)
- Secrets는 코드에 노출하지 않을 것
- 기존 테스트 108개 통과 유지
- `output/` 중 `stable_profile.json`만 예외적으로 커밋
