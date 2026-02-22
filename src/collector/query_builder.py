"""stable_profile.json 기반으로 뉴스 검색 쿼리 세트를 생성한다.

쿼리 설계 원칙 (INITIAL-SCOPE.md 기준):
- top_priorities score 3 항목: 전용 쿼리 생성
- score 2 항목: 상위 카테고리에 포함 (별도 쿼리 없음)
- mode: "trigger" 항목: 이상 시그널 키워드 추가
- mode: "contextual" 항목: 별도 쿼리 없음 (관련 기사에서 자연 포착)
- SK에코플랜트: 전용 쿼리 세트 (D절 참고)
"""

from __future__ import annotations

QUERY_TEMPLATES: list[dict] = [
    {
        "category": "fab_capex",
        "query_en": (
            "(TSMC OR Samsung OR SK hynix OR Intel OR Micron) "
            "AND (fab OR semiconductor plant OR cleanroom) "
            "AND (capex OR expansion OR construction OR groundbreaking)"
        ),
        "query_kr": (
            "(반도체 OR 팹 OR 클린룸) AND (증설 OR 착공 OR 투자 OR CapEx)"
        ),
        "priority": 3,
    },
    {
        "category": "packaging",
        "query_en": (
            "(advanced packaging OR HBM line OR CoWoS OR OSAT) "
            "AND (investment OR capacity OR expansion)"
        ),
        "query_kr": (
            "(첨단패키징 OR HBM OR CoWoS) AND (투자 OR 증설 OR 생산)"
        ),
        "priority": 3,
    },
    {
        "category": "dc_build",
        "query_en": (
            "(data center OR hyperscale OR colocation) "
            "AND (campus OR construction OR MW OR capacity) "
            "AND (power OR cooling OR expansion)"
        ),
        "query_kr": (
            "(데이터센터 OR 하이퍼스케일) AND (신축 OR 전력 OR 냉각 OR MW)"
        ),
        "priority": 3,
    },
    {
        "category": "dc_power",
        "query_en": (
            "(utility interconnection OR substation OR grid constraint OR PPA) "
            "AND data center"
        ),
        "query_kr": (
            "(변전소 OR 계통연계 OR 전력부족 OR PPA) AND 데이터센터"
        ),
        "priority": 3,
    },
    {
        "category": "epc_award",
        "query_en": (
            "(EPC OR contractor OR JV OR procurement) "
            "AND (semiconductor OR data center) "
            "AND (award OR contract OR tender)"
        ),
        "query_kr": (
            "(EPC OR 수주 OR 계약 OR 낙찰) AND (반도체 OR 데이터센터)"
        ),
        "priority": 3,
    },
    {
        "category": "ma_restructure",
        "query_en": (
            "(M&A OR acquisition OR divestiture) "
            "AND (semiconductor OR data center OR construction)"
        ),
        "query_kr": (
            "(M&A OR 인수 OR 매각 OR 사업재편) AND (반도체 OR 건설 OR 데이터센터)"
        ),
        "priority": 3,
    },
    {
        "category": "capex_guidance",
        "query_en": (
            "(capex guidance OR earnings call OR investment plan) "
            "AND (semiconductor OR data center)"
        ),
        "query_kr": (
            "(투자 전망 OR CapEx OR 실적발표) AND (반도체 OR 데이터센터)"
        ),
        "priority": 3,
    },
    {
        "category": "esg_regulation",
        "query_en": (
            "(ESG OR carbon OR emission) "
            "AND (regulation OR investment OR credit OR tax)"
        ),
        "query_kr": (
            "(ESG OR 탄소 OR 배출권) AND (규제 OR 투자 OR 크레딧)"
        ),
        "priority": 3,
    },
    {
        "category": "pf_finance",
        "query_en": (
            "(refinancing OR CMBS OR project finance) "
            "AND (data center OR construction)"
        ),
        "query_kr": (
            "(프로젝트 파이낸스 OR 리파이낸싱 OR PF) AND (데이터센터 OR 건설)"
        ),
        "priority": 3,
    },
    {
        "category": "construction_tech",
        "query_en": (
            "(modular construction OR DfMA OR prefabrication) "
            "AND (data center OR semiconductor OR factory)"
        ),
        "query_kr": (
            "(모듈러 OR DfMA OR 프리팹) AND (데이터센터 OR 반도체 OR 공장)"
        ),
        "priority": 3,
    },
]

SK_ECOPLANT_QUERIES: list[dict] = [
    {
        "category": "sk_ecoplant_order",
        "query_en": (
            '("SK ecoplant" OR "SK에코플랜트") '
            "AND (수주 OR EPC OR contract OR award OR turnkey)"
        ),
        "query_kr": (
            '("SK에코플랜트" OR "SK ecoplant") '
            "AND (수주 OR EPC OR 계약 OR 낙찰 OR 착공)"
        ),
        "priority": 3,
    },
    {
        "category": "sk_ecoplant_finance",
        "query_en": (
            '("SK ecoplant" OR "SK에코플랜트") '
            "AND (차환 OR IPO OR PF OR refinancing OR 우발채무)"
        ),
        "query_kr": (
            '("SK에코플랜트" OR "SK ecoplant") '
            "AND (차환 OR IPO OR PF OR 우발채무 OR 유동성 OR 신용등급)"
        ),
        "priority": 3,
    },
    {
        "category": "sk_ecoplant_strategy",
        "query_en": (
            '("SK ecoplant" OR "SK에코플랜트") '
            'AND ("김영식" OR "AI 인프라" OR strategy OR "사업 재편")'
        ),
        "query_kr": (
            '("SK에코플랜트" OR "SK ecoplant") '
            'AND (김영식 OR "AI 인프라" OR 전략 OR "사업 재편")'
        ),
        "priority": 3,
    },
    {
        "category": "sk_ecoplant_competitor",
        "query_en": (
            "(data center OR semiconductor fab) "
            "AND (EPC OR contractor OR 수주) "
            "AND (Korea OR APAC)"
        ),
        "query_kr": (
            "(데이터센터 OR 반도체) AND (EPC OR 수주 OR 시공) AND (국내 OR 건설사)"
        ),
        "priority": 3,
    },
]

TRIGGER_QUERIES: list[dict] = [
    {
        "category": "material_labor_trigger",
        "query_en": (
            "(construction materials OR labor shortage OR steel price) "
            "AND (surge OR spike OR strike OR shortage)"
        ),
        "query_kr": (
            "(자재 OR 노무 OR 철강 가격) AND (급등 OR 파업 OR 부족 OR 지연)"
        ),
        "priority": 3,
        "mode": "trigger",
    },
    {
        "category": "smartcity_trigger",
        "query_en": (
            "(NEOM OR smart city OR mega project) "
            "AND (contract OR delay OR EPC OR award)"
        ),
        "query_kr": (
            "(네옴 OR 스마트시티 OR 도시개발) AND (수주 OR 지연 OR 착공 OR 계약)"
        ),
        "priority": 3,
        "mode": "trigger",
    },
    {
        "category": "contingent_trigger",
        "query_en": (
            '("SK ecoplant" OR 건설사) '
            "AND (우발채무 OR contingent liability OR PF risk)"
        ),
        "query_kr": (
            '("SK에코플랜트" OR 건설사) AND (우발채무 OR 자금보충 OR PF 리스크)'
        ),
        "priority": 3,
        "mode": "trigger",
    },
]


def build_queries(profile: dict) -> list[dict]:
    """stable_profile.json에서 검색 쿼리 세트를 생성한다.

    score 3인 top_priorities에 대해 매칭되는 템플릿 쿼리를 반환하고,
    SK에코플랜트 전용 쿼리와 trigger 쿼리를 항상 포함한다.
    """
    queries: list[dict] = []

    score_3_categories = _extract_score3_categories(profile)

    for template in QUERY_TEMPLATES:
        if template["category"] in score_3_categories:
            queries.append(template)

    queries.extend(SK_ECOPLANT_QUERIES)
    queries.extend(TRIGGER_QUERIES)

    return queries


def _extract_score3_categories(profile: dict) -> set[str]:
    """프로필에서 score 3인 카테고리 키를 추출한다."""
    cats: set[str] = set()

    for section_key in ("industries", "themes"):
        section = profile.get(section_key, {})
        for key, score in section.items():
            if score >= 3:
                cats.add(key)

    for item in profile.get("top_priorities", []):
        if item.get("score", 0) >= 3:
            name = item.get("name", "")
            mapped = _name_to_category(name)
            if mapped:
                cats.add(mapped)

    return cats


_NAME_CATEGORY_MAP: dict[str, str] = {
    "반도체 Fab/CapEx": "fab_capex",
    "EPC/수주": "epc_award",
    "반도체 메이커": "fab_capex",
    "CapEx 가이던스": "capex_guidance",
    "첨단패키징(HBM/CoWoS)": "packaging",
    "SK그룹/하이닉스": "fab_capex",
    "DC 냉각": "dc_cooling",
    "건설기술(모듈러/DfMA)": "construction_tech",
    "인력/인사": "talent_hr",
    "데이터센터 신축": "dc_build",
    "M&A/사업재편": "ma_restructure",
    "국내 건설사": "epc_award",
    "DC 전력": "dc_power",
    "마일스톤": "milestone",
    "하이퍼스케일러": "dc_build",
    "반도체 장비": "equipment_supply",
    "공기/원가/변경관리": "schedule_cost",
    "SK에코플랜트": "sk_ecoplant_order",
    "인허가": "permit",
    "프로젝트 파이낸싱": "pf_finance",
    "ESG/탄소규제": "esg_regulation",
    "도시개발/스마트시티": "urban_smartcity",
    "우발채무": "contingent",
    "클린룸/공정 인프라": "fab_capex",
    "자재/노무": "material_labor",
    "인프라장비(Schneider/Vertiv)": "infra_equip",
}


def _name_to_category(name: str) -> str | None:
    return _NAME_CATEGORY_MAP.get(name)
