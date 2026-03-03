# News_Agent 세션 핸드오프 — 중복 제거 개선 + 확장 기능

> 세션 시작: 2026-03-03
> 상태: 진행 중

---

## 주제 1 (우선): 뉴스 중복 문제 — 2~3일간 같은 기사 반복 노출

### 현상 (2026-02-22~02-27 실제 데이터)

| 뉴스 | 등장 날짜 | 일수 |
|------|----------|------|
| 최태원 HBM 마진 60% / 증산 발표 | 2/22(2회!), 2/23, 2/24 | 3일 + 당일중복 |
| 신성이엔지 AIO 냉각솔루션 | 2/23, 2/24, 2/25 | 3일 |
| 백사이드 전력공급 양산 | 2/24, 2/25 | 2일 |
| 브이엠-SK하이닉스 463억 장비 | 2/25, 2/26 | 2일 |
| 메타-AMD AI칩 계약 | 2/26, 2/27 | 2일 |
| SK에코플랜트 하이테크솔루션 졸업 | 2/26, 2/27 | 2일 |

추가 문제: 2/22 Top5의 #3과 #4가 동일 헤드라인 (같은 날 내부 중복).

### 원인 분석

#### 원인 1: Google News `when:2d` 수집 윈도우

`src/collector/gnews_client.py` line 45-49:
```python
when_param = f"+when:{recent_days}d" if recent_days else ""
# recent_days 기본값 = 2 → "when:2d"
```
- 2일치 기사를 수집하므로, 어제 수집된 기사가 오늘도 당연히 다시 수집됨
- 뉴스 가치가 높은 기사일수록 2일째에도 Google News 랭킹 상위에 머물러 재수집 확률 ↑

#### 원인 2: 교차-날짜 중복 제거 부재

`src/collector/dedup.py`:
- **당일 수집분** 내에서만 URL/제목 중복 제거
- 이전 날짜에 이미 Top5로 다뤘던 기사와의 비교 로직 **없음**
- `cmd_collect`(main.py)는 이전 날짜 데이터를 참조하지 않음

#### 원인 3: Stage 1 LLM이 과거 브리핑을 모름

`src/briefer/prompts.py` STAGE1_SYSTEM:
- "같은 사건의 중복 기사는 대표 1건만 선정" 규칙은 있지만
- **이전 날짜 Top5 헤드라인**을 프롬프트에 주입하지 않음
- LLM은 오늘 수집된 기사만 보고 판단 → 어제 이미 다룬 뉴스를 다시 Top5에 올림

#### 원인 4: `_dedup_top5` 버그 (같은 날 내부 중복)

`src/briefer/briefing_generator.py` line 332-349:
```python
title_short = title[:30]
if any(title_short in seen or seen in title_short
       for seen in seen_titles):
```
- `seen`이 변수명이 리스트의 element를 순회하는 루프 변수인데 `seen_titles`와 혼동 아님
- 로직 자체는 맞지만, 2/22 데이터에서 같은 제목이 2번 등장 → **Stage 1 LLM이 동일 기사 ID를 2번 반환**했을 가능성
- 또는 **동일 기사가 다른 ID로 수집**되어 제목은 같지만 ID가 다른 경우
- 제목 앞 30자가 약간이라도 다르면(공백, 기호 차이) 통과될 수 있음

### CI 환경 제약사항 (검수에서 발견)

```
daily-briefing.yml 워크플로우:
  - git add web/  ← web/ 디렉토리만 커밋
  - output/ 디렉토리는 커밋되지 않음
  → output/briefings/*.json은 CI 런 간 영속되지 않음!
  → 교차 dedup 데이터 소스로 web/ 내 파일을 사용해야 함
```

### 해결 방안 (수정)

#### Step 1: `_dedup_top5` 강화 — 같은 날 내부 중복 방지

**문제**: 2/22에 Top5 #3과 #4가 동일 헤드라인.
**원인**: 제목 앞 30자 prefix 비교 방식이 공백/기호 차이에 취약.
**수정**: Jaccard 토큰 유사도(임계값 0.5)로 교체. collector의 `dedup.py`와 동일 방식.

구현 위치: `src/briefer/briefing_generator.py` `_dedup_top5()`

#### Step 2: `top5-history.json` 인프라 — 이전 날짜 데이터 영속화

**문제**: `output/`가 CI에서 영속되지 않아 이전 Top5 참조 불가.
**수정**: `web/top5-history.json`에 매일 Top5 헤드라인을 누적 저장.
- `cmd_brief` 완료 후 당일 top5 헤드라인을 `web/top5-history.json`에 추가
- 최근 7일분만 유지 (오래된 항목 자동 정리)
- `git add web/`이 이미 이 파일을 포함하므로 워크플로우 변경 불필요

```json
{
  "2026-02-27": ["헤드라인1", "헤드라인2", ...],
  "2026-02-26": ["헤드라인1", "헤드라인2", ...],
  ...
}
```

구현 위치: `src/main.py` `cmd_brief()`, `src/config.py`

#### Step 3: Stage 1 프롬프트에 이전 Top5 주입 — LLM이 기존 뉴스 인지

**수정**: `build_stage1_prompt()`에 이전 Top5 컨텍스트 추가.
```
"아래는 최근 3일간 이미 Top 5로 다룬 헤드라인입니다.
동일 사건의 후속 보도(새로운 팩트가 추가된 경우)가 아닌 한,
이 헤드라인들을 오늘 Top 5에서 제외하세요:
- 2/26: [헤드라인 5개]
- 2/25: [헤드라인 5개]
- 2/24: [헤드라인 5개]"
```

구현 위치: `src/briefer/prompts.py`, `src/briefer/briefing_generator.py`

#### 보류: `when:2d` → `when:1d` 변경

- 장점: 근본적으로 어제 기사 재수집 방지
- 단점: 수집 기사 수 급감 위험 (특히 주말/공휴일)
- 판단: Step 2+3으로 충분히 해결 가능, 1d는 리스크 큼. 적용 후 재평가

### 구현 순서

| Step | 내용 | 예상 공수 | 의존성 |
|------|------|----------|--------|
| 1 | `_dedup_top5` Jaccard 교체 | 30분 | 없음 |
| 2 | `top5-history.json` 인프라 | 1시간 | 없음 |
| 3 | Stage 1 프롬프트 이전 Top5 주입 | 1~2시간 | Step 2 |
| **총** | | **2.5~3.5시간** | |

각 Step 완료 후 단위 테스트 + 코드 리뷰 진행.

---

## 주제 2: 확장 기능 구현 — 피드백 + 검색/챗봇

(주제 1 완료 후 진행)

### 피드백 기능 (IMPROVEMENT-BACKLOG #2)
- 상세 설계: `docs/HANDOFF-feedback-rag.md`
- VPS FastAPI 백엔드 + SQLite
- 예상 공수: 8~12시간

### 검색/챗봇 기능 (IMPROVEMENT-BACKLOG #3)
- 상세 설계: `docs/HANDOFF-feedback-rag.md`
- SQLite FTS5 + LLM (Haiku)
- 예상 공수: 12~16시간

### 추가 미착수 과제
- 텍스트 버전 근본 재설계 (#1, 보류)
- 프리셋 확장 (#4, 낮은 우선순위)

논의 사항: 구현 우선순위, VPS 환경 구성, 프론트엔드/백엔드 분리 전략.

---

## 변경 이력

| 날짜 | 내용 |
|------|------|
| 2026-03-03 | 문서 작성, 주제 1 원인 분석 및 방안 정리 |
| 2026-03-03 | Step 1~3 구현 완료, 26개 테스트 전부 통과 |
