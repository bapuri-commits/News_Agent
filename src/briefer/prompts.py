"""브리핑 생성 단계별 LLM 프롬프트 템플릿.

4단계 파이프라인:
  Stage 1 (Sonnet): 클러스터링 + Top 5 선정
  Stage 2 (Opus):   Top 5 심층 요약 (본문 기반)
  Stage 3 (Sonnet): 카테고리별 요약
  Stage 4 (Opus):   SK에코플랜트 렌즈 분석
"""

STAGE1_SYSTEM = """\
당신은 건설/반도체/데이터센터/인프라 업계 임원을 위한 뉴스 분석가입니다.

역할: 오늘 수집된 기사들을 분석하여 (1) Top 5 선정, (2) 카테고리별 그룹핑을 수행합니다.

판단 기준 (우선순위):
- score 3 카테고리(반도체 Fab/CapEx, EPC/수주, DC 인프라 등)에 해당하는 기사 우선
- 대형 수주, 차환/리파이낸싱 이벤트는 무조건 Top 5 후보
- 같은 사건의 중복 기사는 대표 1건만 선정
- 소스 다양성 고려 (한국어/영어 혼합, S1~S7 분산)

sk_ecoplant_ids 선정 규칙 (엄격하게 적용):
- "SK에코플랜트" 또는 "SK ecoplant"가 제목에 직접 등장하는 기사만 포함
- 단순히 반도체/건설/EPC 관련이라고 포함하지 말 것
- 일반적인 산업 뉴스는 해당 카테고리 클러스터에만 배치
- 최대 10건 이내로 제한

출력은 반드시 아래 JSON 스키마대로만 응답하라. 설명 없이 순수 JSON만 출력.
"""

STAGE1_OUTPUT_SCHEMA = """\
{
  "top5_ids": ["기사id1", "기사id2", "기사id3", "기사id4", "기사id5"],
  "sk_ecoplant_ids": ["SK에코플랜트 관련 기사 id 리스트"],
  "clusters": {
    "fab_capex": ["기사id", ...],
    "dc_build": ["기사id", ...],
    "epc_award": ["기사id", ...],
    "ma_restructure": ["기사id", ...],
    "esg_regulation": ["기사id", ...],
    "pf_finance": ["기사id", ...],
    "sk_ecoplant": ["기사id", ...],
    "other": ["기사id", ...]
  },
  "excluded_ids": ["관련성 낮아 제외된 기사 id"],
  "reasoning": "Top 5 선정 이유 (한국어, 2-3문장)"
}
"""


STAGE2_SYSTEM = """\
당신은 건설/반도체/데이터센터 업계 임원에게 아침 브리핑을 작성하는 전문가입니다.

역할: 주어진 기사의 본문을 읽고 임원 브리핑 형식으로 구조화합니다.

각 기사에 대해 반드시 4가지를 추출하라:
- Fact: 확인된 사실 (계약/금액/일정/프로젝트 위치/발주처/수주자/공기). 숫자와 고유명사 중심.
- Impact: 업계/회사에 미치는 의미 (수주믹스, 수익성, 현금흐름 타이밍 등)
- Risk: 리스크 요인 (인허가/전력/PF/차환/원가상승/변경관리)
- Next Signal: 향후 1~2주 내 확인해야 할 후속 사항

원칙:
- 한국어로 작성
- Fact와 추론(Impact/Risk)을 명확히 구분
- 출처 없는 주장은 "미확인" 표시
- 간결하되 핵심 수치/이름은 반드시 포함

출력은 반드시 아래 JSON 스키마대로만 응답하라.
"""

STAGE2_OUTPUT_SCHEMA = """\
{
  "items": [
    {
      "id": "기사id",
      "headline": "핵심 한줄 요약 (한국어, 40자 이내)",
      "category": "주요 카테고리 키 (fab_capex, dc_build, epc_award 등)",
      "fact": "확인된 사실 (2-3문장)",
      "impact": "업계/회사 영향 (1-2문장)",
      "risk": "리스크 요인 (1-2문장, 없으면 '특이사항 없음')",
      "next_signal": "후속 확인 사항 (1문장)",
      "sources": [{"name": "출처명", "url": "기사URL"}]
    }
  ]
}
"""


STAGE3_SYSTEM = """\
당신은 뉴스 분석가입니다. 같은 카테고리에 속한 기사들을 묶어 카테고리 단위 요약을 작성합니다.

원칙:
- 한국어로 작성
- 카테고리 전체 동향을 2-3문장으로 요약
- 개별 기사는 제목 + 핵심 한줄로 축약
- 같은 사건의 중복은 병합

출력은 반드시 아래 JSON 스키마대로만 응답하라.
"""

STAGE3_OUTPUT_SCHEMA = """\
{
  "categories": {
    "카테고리키": {
      "summary": "이 카테고리의 전체 동향 요약 (한국어, 2-3문장)",
      "items": [
        {
          "id": "기사id",
          "headline": "한줄 요약",
          "fact": "핵심 사실 (1문장)"
        }
      ]
    }
  }
}
"""


STAGE4_SYSTEM = """\
당신은 SK에코플랜트(김영식 CEO) 전문 애널리스트입니다.

역할: SK에코플랜트 관련 기사를 4가지 렌즈로 분석합니다.

4대 렌즈:
1. 수주·믹스 변화 (order_mix): 반도체/AI 인프라 비중 상승 여부, 신규 수주 현황
2. 현금흐름·차입 구조 (cashflow): 단기차입 비중, 차환/금리, 유동성 이벤트
3. PF 우발/리스크 (pf_contingent): 자금보충약정, 우발채무, 프로젝트 리스크
4. IPO·포트폴리오 정리 (competitor): 상장 신호, 자회사/지분 매각, 경쟁사 동향

원칙:
- 한국어로 작성
- 숫자는 "주장(Claim)"으로 표기하고 기사 근거/기준시점을 함께 기록
- 확인된 Fact와 추론을 명확히 구분
- 해당 렌즈에 뉴스가 없으면 "해당 기간 특이사항 없음"

출력은 반드시 아래 JSON 스키마대로만 응답하라.
"""

STAGE4_OUTPUT_SCHEMA = """\
{
  "headline": "SK에코플랜트 오늘의 핵심 (한줄, 30자 이내)",
  "order_mix": "수주·믹스 분석 (2-3문장)",
  "cashflow": "현금흐름·차입 분석 (2-3문장)",
  "pf_contingent": "PF/우발채무 분석 (2-3문장)",
  "competitor": "IPO/경쟁사 분석 (2-3문장)",
  "sources": [{"name": "출처명", "url": "URL"}]
}
"""


def build_stage1_prompt(articles: list[dict], profile_summary: str) -> str:
    """Stage 1: 기사 목록 + 프로필 요약 → 클러스터링/Top5 선정 프롬프트."""
    article_lines = []
    for a in articles:
        line = (
            f"- id:{a['id']} | {a['title'][:80]} | "
            f"source:{a['source_name']} ({a['source_group']}) | "
            f"cat:{','.join(a.get('categories', []))} | "
            f"score:{a.get('relevance_score', 0):.2f} | "
            f"lang:{a['language']}"
        )
        article_lines.append(line)

    return (
        f"## 독자 프로필 요약\n{profile_summary}\n\n"
        f"## 오늘의 기사 ({len(articles)}건)\n"
        + "\n".join(article_lines)
        + f"\n\n## 출력 스키마\n{STAGE1_OUTPUT_SCHEMA}"
    )


def build_stage2_prompt(articles_with_body: list[dict]) -> str:
    """Stage 2: Top 5 기사 (본문 포함) → 심층 Fact/Impact/Risk/Next."""
    sections = []
    for a in articles_with_body:
        sections.append(
            f"### 기사 id:{a['id']}\n"
            f"제목: {a['title']}\n"
            f"출처: {a['source_name']} ({a['source_group']})\n"
            f"URL: {a.get('url', '')}\n"
            f"카테고리: {','.join(a.get('categories', []))}\n"
            f"본문:\n{a['body']}\n"
        )

    return (
        "\n---\n".join(sections)
        + f"\n\n## 출력 스키마\n{STAGE2_OUTPUT_SCHEMA}"
    )


def build_stage3_prompt(clusters: dict[str, list[dict]]) -> str:
    """Stage 3: 카테고리별 기사 → 카테고리 요약."""
    sections = []
    for cat, articles in clusters.items():
        lines = []
        for a in articles:
            lines.append(
                f"  - id:{a['id']} | {a['title'][:70]} | "
                f"{a.get('snippet', '')[:150]}"
            )
        sections.append(f"### {cat} ({len(articles)}건)\n" + "\n".join(lines))

    return (
        "\n\n".join(sections)
        + f"\n\n## 출력 스키마\n{STAGE3_OUTPUT_SCHEMA}"
    )


def build_stage4_prompt(sk_articles: list[dict]) -> str:
    """Stage 4: SK에코플랜트 관련 기사 → 4대 렌즈 분석."""
    sections = []
    for a in sk_articles:
        sections.append(
            f"### 기사 id:{a['id']}\n"
            f"제목: {a['title']}\n"
            f"출처: {a['source_name']}\n"
            f"URL: {a.get('url', '')}\n"
            f"본문:\n{a['body']}\n"
        )

    return (
        "\n---\n".join(sections)
        + f"\n\n## 출력 스키마\n{STAGE4_OUTPUT_SCHEMA}"
    )


def build_profile_summary(profile: dict) -> str:
    """stable_profile.json에서 LLM에 전달할 프로필 요약을 생성한다."""
    top_prio = [
        f"{p['name']}(score:{p['score']})"
        for p in profile.get("top_priorities", [])[:10]
    ]
    triggers = profile.get("must_include_triggers", [])
    avoid = profile.get("avoid", [])
    sk_lens = profile.get("sk_ecoplant_lens", [])

    return (
        f"- 핵심 관심사: {', '.join(top_prio)}\n"
        f"- 필수 포함 트리거: {', '.join(triggers)}\n"
        f"- 회피: {', '.join(avoid)}\n"
        f"- SK에코플랜트 렌즈: {', '.join(sk_lens)}\n"
        f"- 요약 언어: 한국어\n"
        f"- 읽기 시간: {profile.get('preferred_format', {}).get('reading_time', '20min')}"
    )
