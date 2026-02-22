"""브리핑 모듈 공용 상수.

카테고리 체계 (INITIAL-SCOPE.md 16개 서브스코프 기반):
  A. 반도체: fab_capex, cleanroom, equipment_supply, packaging
  B. 데이터센터: dc_build, dc_power, dc_cooling
  C. 건설/수주: epc_award, schedule_cost, permit, safety, material_labor
  D. 투자/정책: capex_guidance, pf_finance, ma_restructure, policy_subsidy
  +  테마: esg_regulation, construction_tech, talent_hr, urban_smartcity, contingent
  +  전용: sk_ecoplant
"""

CATEGORY_LABELS = {
    # A. 반도체 Fab / 공급망 / CapEx
    "fab_capex": "반도체 Fab / CapEx",
    "cleanroom": "클린룸 / 공정 인프라",
    "equipment_supply": "장비 / 부품 공급망",
    "packaging": "첨단 패키징",
    # B. 데이터센터 / AI 인프라
    "dc_build": "데이터센터 신축",
    "dc_power": "DC 전력",
    "dc_cooling": "DC 냉각",
    # C. 건설 / 수주 / 프로젝트 리스크
    "epc_award": "EPC / 수주",
    "schedule_cost": "공기 / 원가 / 변경관리",
    "permit": "인허가 / 환경",
    "safety": "안전 / 품질 / 컴플라이언스",
    "material_labor": "자재 / 노무",
    # D. 투자 / 정책 / 시장 사이클
    "capex_guidance": "CapEx 가이던스",
    "pf_finance": "프로젝트 파이낸싱",
    "ma_restructure": "M&A / 사업재편",
    "policy_subsidy": "정책 / 보조금",
    # 테마
    "esg_regulation": "ESG / 탄소규제",
    "construction_tech": "건설기술",
    "talent_hr": "인력 / 인사",
    "urban_smartcity": "도시개발 / 스마트시티",
    "contingent": "우발채무 / PF 리스크",
    # 전용 추적
    "sk_ecoplant": "SK에코플랜트",
    "other": "기타",
}

CATEGORY_COLORS = {
    "fab_capex": "#1a73e8",
    "cleanroom": "#3b82f6",
    "equipment_supply": "#6366f1",
    "packaging": "#8b5cf6",
    "dc_build": "#7c3aed",
    "dc_power": "#0891b2",
    "dc_cooling": "#06b6d4",
    "epc_award": "#16a34a",
    "schedule_cost": "#15803d",
    "permit": "#ca8a04",
    "safety": "#b91c1c",
    "material_labor": "#a16207",
    "capex_guidance": "#2563eb",
    "pf_finance": "#ea580c",
    "ma_restructure": "#dc2626",
    "policy_subsidy": "#4f46e5",
    "esg_regulation": "#65a30d",
    "construction_tech": "#9333ea",
    "talent_hr": "#0d9488",
    "urban_smartcity": "#0284c7",
    "contingent": "#e11d48",
    "sk_ecoplant": "#f97316",
    "other": "#6b7280",
}

SOURCE_GROUP_LABELS = {
    "S1": "DC전문",
    "S2": "반도체전문",
    "S3": "기업공시",
    "S4": "리서치",
    "S5": "건설전문",
    "S6": "종합경제지",
    "S7": "국내매체",
}
