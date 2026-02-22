# Phase 9 핸드오프 프롬프트

> 이 문서를 새 Cursor 세션에 통째로 붙여넣으면 Phase 9 작업을 이어갈 수 있다.

---

## 프로젝트 개요

**News_Agent**는 가족 내부용 임원 뉴스 브리핑 에이전트. Phase 1~8 완료. Phase 9에서 **이메일 알림**을 추가하여, 매일 아침 아버지 메일함에 브리핑 본문이 직접 도착하도록 한다.

**현재 자동 워크플로우 (Phase 8 완료):**
```
매일 KST 06:00 (UTC 21:00)
  → GitHub Actions: collect → brief → deploy → push → Pages 배포
  → https://bapuri-commits.github.io/News_Agent/
```

**Phase 9 목표:** 브리핑 배포 완료 시 이메일로 브리핑 HTML 본문 전송. 파이프라인 실패 시에도 실패 알림 이메일 전송.

---

## Phase 1~8 완료 상태

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
  Phase 8: GitHub Actions 자동 스케줄링 (매일 KST 06:00)
    → 워크플로우 실행 확인: ~3분, collect + brief + deploy + Pages 배포
    → 배포 URL: https://bapuri-commits.github.io/News_Agent/
```

---

## Phase 9: 이메일 알림 — 해야 할 작업

### 목표

1. **성공 알림**: 브리핑 배포 완료 시 이메일 전송
   - 제목: "📰 2026-02-22 Executive Briefing"
   - 본문: 브리핑 HTML 전체 (메일만 열면 바로 읽을 수 있음)
2. **실패 알림**: 파이프라인 실패 시 이메일로 에러 알림
   - 제목: "❌ 2026-02-22 브리핑 파이프라인 실패"
   - 본문: 실패 날짜 + GitHub Actions 로그 링크
3. **배포 실패 알림**: Pages 배포만 실패 시 별도 알림
   - 제목: "❌ 2026-02-22 페이지 배포 실패"
   - 본문: 브리핑 생성 완료 안내 + 로그 링크

### 구현 방식

**GitHub Actions의 `dawidd6/action-send-mail@v3` 액션 사용**
- Gmail SMTP를 통해 이메일 발송
- `html_body: file://web/{date}.html`로 브리핑 HTML을 메일 본문에 직접 삽입
- 추가 Python 코드 없음, 워크플로우만 수정

### 사전 준비 (수동)

#### 1. Gmail 앱 비밀번호 생성

1. 발신용 Gmail 계정에 **2단계 인증** 활성화 (이미 활성화돼 있으면 건너뛰기)
   - Google 계정 → 보안 → 2단계 인증 → 사용
2. **앱 비밀번호** 생성
   - Google 계정 → 보안 → 앱 비밀번호 (또는 https://myaccount.google.com/apppasswords)
   - 앱 선택: "메일", 기기 선택: "기타" → 이름 입력 (예: "News Agent")
   - 생성된 16자리 비밀번호 복사 (예: `abcd efgh ijkl mnop`)
   - ⚠️ 이 비밀번호는 다시 볼 수 없으니 바로 Secrets에 등록

#### 2. GitHub Secrets 등록

레포 Settings → Secrets and variables → Actions → New repository secret:
- `EMAIL_USERNAME`: 발신 Gmail 주소 (예: `sender@gmail.com`)
- `EMAIL_PASSWORD`: 위에서 생성한 앱 비밀번호 (16자리, 공백 제거)
- `EMAIL_TO`: 수신 이메일 주소 (아버지 이메일)

### 구현 완료된 변경

#### `.github/workflows/daily-briefing.yml` 수정

**변경 1: `briefing` job에 `outputs` 추가** — 날짜를 다른 job에서 참조할 수 있도록:

```yaml
  briefing:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    outputs:
      target_date: ${{ steps.date.outputs.target }}
```

**변경 2: `briefing` job 마지막에 성공/실패 이메일 step 추가:**

```yaml
      - name: Email briefing
        if: success()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "📰 ${{ steps.date.outputs.target }} Executive Briefing"
          to: ${{ secrets.EMAIL_TO }}
          from: ${{ secrets.EMAIL_USERNAME }}
          html_body: file://web/${{ steps.date.outputs.target }}.html
        continue-on-error: true

      - name: Email failure alert
        if: failure()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "❌ ${{ steps.date.outputs.target }} 브리핑 파이프라인 실패"
          to: ${{ secrets.EMAIL_TO }}
          from: ${{ secrets.EMAIL_USERNAME }}
          body: |
            브리핑 파이프라인이 실패했습니다.

            날짜: ${{ steps.date.outputs.target }}
            로그: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        continue-on-error: true
```

**변경 3: `deploy-pages` job에 배포 실패 알림 추가:**

```yaml
      - name: Email deploy failure
        if: failure()
        uses: dawidd6/action-send-mail@v3
        with:
          server_address: smtp.gmail.com
          server_port: 465
          username: ${{ secrets.EMAIL_USERNAME }}
          password: ${{ secrets.EMAIL_PASSWORD }}
          subject: "❌ ${{ needs.briefing.outputs.target_date }} 페이지 배포 실패"
          to: ${{ secrets.EMAIL_TO }}
          from: ${{ secrets.EMAIL_USERNAME }}
          body: |
            GitHub Pages 배포가 실패했습니다.
            (브리핑 생성은 완료, 배포 단계에서 오류)

            로그: ${{ github.server_url }}/${{ github.repository }}/actions/runs/${{ github.run_id }}
        continue-on-error: true
```

### 설계 결정

| 결정 | 이유 |
|------|------|
| `continue-on-error: true` | 이메일 발송 실패가 전체 파이프라인을 실패시키지 않도록 |
| `html_body: file://` | 브리핑 HTML을 메일 본문에 직접 삽입 — 링크 클릭 없이 바로 읽기 가능 |
| `deploy-pages` job에도 실패 알림 | 브리핑 생성은 성공했지만 배포만 실패하는 경우 커버 |
| `outputs` 사용 | job 간 날짜 변수 공유 (deploy-pages에서 날짜 참조용) |
| 텔레그램 보류 | 이메일이 기존 루틴에 자연스럽게 편입, 필요 시 step 추가만으로 확장 가능 |

### 실행 시나리오

```
매일 UTC 21:00 (KST 06:00)
    ↓
① collect → brief → deploy → push
    ↓ (성공 시)
② 이메일: "📰 2026-02-23 Executive Briefing" (HTML 본문 포함)
    ↓
③ Pages 배포
    ↓ (배포 실패 시)
④ 이메일: "❌ 2026-02-23 페이지 배포 실패"
    ↓
아버지 메일함에 브리핑 도착 (메일만 열면 바로 읽기 가능)
```

### 주의사항

- `if: failure()` step은 이전 step이 실패해도 실행됨
- `if: success()`는 모든 이전 step이 성공해야 실행
- `continue-on-error: true`로 이메일 실패가 job 실패를 유발하지 않음
- Gmail SMTP는 일 500건 제한 (하루 1건이므로 문제 없음)
- 브리핑 HTML의 `<script>` 태그는 이메일 클라이언트에서 무시됨 (카드 접기 기능 비작동, 읽기에는 지장 없음)

### 비용

| 항목 | 비용 |
|------|------|
| Gmail SMTP | 무료 |
| `dawidd6/action-send-mail` 액션 | 무료 |
| GitHub Actions 추가 시간 | ~2초 |
| **총 추가 비용** | **$0** |

---

## 참조 파일 위치

| 파일 | 용도 |
|------|------|
| `.github/workflows/daily-briefing.yml` | Phase 8 워크플로우 (**Phase 9에서 수정 완료**) |
| `.github/workflows/deploy-pages.yml` | 기존 Pages 배포 (변경 불필요) |
| `src/main.py` | CLI 진입점 (변경 불필요) |
| `src/config.py` | 경로 상수 (변경 불필요) |
| `src/deployer/site_builder.py` | 정적 사이트 빌더 (Phase 8에서 수정됨) |
| `output/stable_profile.json` | 프로필 (gitignore 예외, 커밋됨) |
| `.env` | ANTHROPIC_API_KEY (로컬용) |

---

## 코드 구조 (현재 + Phase 9 변경분)

```
.github/
  workflows/
    deploy-pages.yml          # Phase 7 (변경 없음)
    daily-briefing.yml        # Phase 8 → Phase 9에서 이메일 알림 step 추가 ✅

src/                          # Phase 9에서 변경 없음
  main.py
  config.py
  collector/
  briefer/
  deployer/
    site_builder.py            # Phase 8에서 수정됨 (CI 호환)
    nav_injector.py            # Phase 8에서 수정됨 (strip_nav 추가)
    index_generator.py
```

---

## 구현 순서

1. ✅ `daily-briefing.yml` 수정 — 이메일 알림 step 추가
2. Gmail 앱 비밀번호 생성 (수동)
3. GitHub Secrets에 `EMAIL_USERNAME`, `EMAIL_PASSWORD`, `EMAIL_TO` 등록 (수동)
4. `workflow_dispatch`로 수동 테스트
5. 이메일 수신 확인

---

## 향후 개선 과제 (Phase 10+)

> `docs/IMPROVEMENT-BACKLOG.md`에 상세 내용 있음

| # | 과제 | 우선순위 | 예상 공수 |
|---|------|---------|----------|
| 0 | 텔레그램 알림 추가 (이메일과 병행) | 선택 | 30분 |
| 1 | 본문 크롤링 개선 (Playwright/base64 디코딩) | 높음 | 2~3시간 |
| 2 | 카테고리별 요약 심화 (Impact 필드 추가) | 중간 | 1~2시간 |
| 3 | 뉴스 수집 튜닝 (2-gram 키워드, S7 비중 조정) | 중간 | 2~4시간 |
| 4 | 사용자 피드백 기능 (브리핑 내 👍/👎) | 낮음 | 6~8시간 |
| 5 | 검색용 채팅 기능 (과거 브리핑 RAG 검색) | 낮음 | 8~12시간 |
| 6 | HTML 테마 재설계 | 낮음 | 3~5시간 |

---

## 규칙

- 한국어로 응답
- 파일 수정 전 반드시 읽기 먼저
- GitHub Actions YAML은 정확한 들여쓰기 (2칸 space)
- Secrets는 코드에 노출하지 않을 것
- 기존 테스트 108개 통과 유지
