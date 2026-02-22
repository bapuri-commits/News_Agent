[CURSOR PROMPT — Family-Only Executive News Briefing Agent (Design + Skeleton Plan)]

ROLE
You are a senior engineer + architect designing a “family internal news briefing agent” specialized for an executive reader.
Goal: Every morning, enable father (an executive tracking Construction + Data Centers + Semiconductor Fab + Investment/Finance/IPO trends, especially around SK ecoplant) to grasp key signals within 5–20 minutes.

CORE OUTPUTS (2-track)
A) Evidence-preserving TEXT BRIEF (accuracy-first)
- Must preserve original source + link(s) for every claim.
- Must separate Fact vs Inference.
- Must include numbers only with “as-of date” + source.

B) Readable HTML BRIEF (consumption-first)
- Card/section based HTML view (timeline, stakeholders, risks/opportunities, next signals, source diversity distribution).
- Designed for mobile viewing.
- HTML must be generated automatically and archived daily.

IMPORTANT: Split responsibilities into two roles for quality:
1) Summarizer
   - Extract facts/numbers/claims + opposing viewpoints.
   - Attach links, as-of dates, and confidence markers.
   - Output must be structured JSON for downstream use.
2) Formatter (UI Writer)
   - Convert Summarizer JSON into a beautiful HTML briefing:
     - cards / sections / tables / highlights
     - must include source links and “source-group distribution” footer
   - Implementation can start with a deterministic HTML template engine.
   - Later, can swap/extend with Opal or a dedicated UI-generation AI/MCP.
   - Keep Formatter as an interface boundary (pluggable).

SYSTEM CONSTRAINTS / PRIORITIES
- Family-only. No need for public deployment or multi-tenant SaaS concerns.
- Ignore cost/inefficiency if it improves security and performance.
- Security and performance (fast, stable) are top priority.
- Avoid “recommendation algorithm drift” / bias amplification:
  - Stable Profile + Keyword/Scope are primary.
  - Conversation context is only a shallow hint (e.g., 5–10% weight max).
  - Source/stance diversity constraints always override personalization.
- Home hosting is currently NOT possible.
  - Preferred option: VPS (near Korea region) + VPN-only access (WireGuard/Tailscale) + private web app.
  - Minimize exposed ports; prefer web only inside VPN.
  - DB/storage on server; consider disk encryption + backups.
  - Optional: Telegram used only as a “notification channel” (generation done + private link), not full content store.

USER FLOW (END-TO-END)
1) Scheduler runs daily at a fixed time (e.g., 06:00–07:00 Asia/Seoul).
2) Collect articles from sources (RSS, official PR/IR, industry media, finance media).
3) Normalize/clean:
   - language detect
   - deduplicate
   - event clustering (same story across outlets)
   - tagging by topics + source-group classification
   - credibility/source metadata
4) Rank/select:
   - scope relevance + importance (novelty/impact/follow-up coverage) + diversity constraints + (conversation hint * small weight)
5) Generate outputs:
   (A) Text brief: 5-min Top 5 + category highlights + links
   (B) HTML brief: card/section view (timeline, stakeholders, risks/opps, next signals, source diversity)
6) Store/archive daily briefings for browsing (history).
7) Provide an interactive Q&A / chat:
   - Chat influences next-day collection only shallowly (5–10% max), never breaking diversity guardrails.

INITIAL SCOPE REQUIREMENTS
A) Core topic tree (4 pillars → 12 subscopes)
[A. Semiconductor Fab / Supply Chain / CapEx]
- A1. Fab expansion / CapEx / schedule (groundbreaking, ramp, delay)
- A2. Cleanroom / process infra (UPW, CDA, chemicals, gases, exhaust/abatement/scrubbers)
- A3. Equipment & parts supply chain (ASML, AMAT, Lam, TEL / valves, pumps, chemicals)
- A4. Advanced packaging (CoWoS, HBM line, OSAT)

[B. Data Center / AI Infrastructure]
- B1. Hyperscale/colocation buildouts/campuses (MW capacity, land, leasing)
- B2. Power (utility interconnection, PPA, substation, grid constraints)
- B3. Cooling (liquid/immersion, CDU, density, environmental/regulatory)
- B4. Cloud/network (major operators’ regions, capex changes, delays)

[C. Construction / Awards / Project Risk]
- C1. EPC/GC awards, JV/subcontract structure, schedule/cost risk
- C2. Permitting/environment/community opposition (esp. DC)
- C3. Safety/quality/compliance (hazmat, cleanroom standards)
- C4. Materials/labor/equipment supply (price/lead time)

[D. Investment/Policy/Market Cycle]
- D1. Policy/subsidies (CHIPS-like, tax credits, regulation)
- D2. Corporate capex guidance (increase/decrease, ramp plans)
- D3. Finance (project finance, refinancing, CMBS)
- D4. IPO/valuation (builders, infra developers/operators)

B) Global keyword set (KR/EN mixed; start broad)
- Semiconductor players: TSMC, Samsung, SK hynix, Intel, Micron, GF, TI, UMC, SMIC
- DC players: AWS, Microsoft, Google, Oracle, Meta, Equinix, Digital Realty, QTS, CyrusOne, Switch, NTT, GDS
- Infra/equipment: ASML, Applied Materials, Lam, TEL, KLA / Schneider, Vertiv, Eaton, ABB, Siemens, Legrand
- Fab KR/EN keywords: 팹 증설, 라인 증설, 클린룸, UPW, CDA, scrubber, abatement, specialty gases, HBM, advanced packaging, ramp, delay
- DC KR/EN keywords: 데이터센터 신축, MW, 계통연계, 변전소, PPA, grid constraint, liquid cooling, immersion cooling, heat density
- Finance/Policy KR/EN keywords: 보조금, tax credits, permitting, project finance, refinancing, CMBS, capex guidance, IPO

C) Query templates (generate 30–200 docs/day, then cluster+dedupe to 20–40 final)
- Fab/CapEx:
  (<company> OR <region>) AND (fab OR semiconductor plant OR cleanroom) AND (capex OR expansion OR construction OR groundbreaking OR ramp OR delay)
  (advanced packaging OR HBM line) AND (investment OR capacity OR equipment)
- DC/Power:
  (data center campus OR hyperscale OR colocation) AND (MW OR capacity) AND (<region> OR <company>)
  (utility interconnection OR substation OR grid constraint OR PPA) AND data center
- Construction/Awards:
  (EPC OR contractor OR JV OR procurement) AND (data center OR semiconductor) AND (award OR contract OR tender)
  (permitting OR zoning OR environmental) AND data center AND (<region>)
- Finance:
  (refinancing OR CMBS OR project finance) AND data center
  (capex guidance OR earnings call) AND (semiconductor OR data center)

D) Source groups (for diversity enforcement)
- S1 DC-specialist (e.g., DatacenterDynamics)
- S2 Semiconductor-specialist (e.g., EE Times; candidates: Semiconductor Engineering, SEMI, SIA)
- S3 Official PR/IR/filings (company pressrooms, disclosures)
- S4 Research/consulting (McKinsey, SIA reports, etc.)
- S5 Construction industry (e.g., ENR; public tender DB candidates)
- S6 Broad finance/news (FT/WSJ/Reuters/Bloomberg/Nikkei; paywalled OK)
- S7 Korea local sources (Yonhap, Hankyung, Maeil, ChosunBiz, ETNews, TheElec, TheBell, public notices)

Operational rule: every daily brief must show “source-group distribution” and enforce minimum diversity quotas.

SK ECOPLANT / CEO WATCH (Specialized overlay)
1) “Lens” (fixed in the briefing format daily)
- Order-mix shift: semiconductor/AI infra share actually increasing?
- Cashflow & debt structure: short-term debt ratio, refinancing cost, liquidity events
- PF contingent liabilities: support obligations/guarantees shrinking?
- IPO & portfolio cleanup: asset/stake sales, restructuring, official IPO signals

2) Fixed entities / keywords
- People/structure: 김영식, 장동현, 각자대표, 대표이사 사장/부회장
- Company: SK에코플랜트, SK ecoplant
- Strategy: AI 인프라 밸류체인, 반도체 인프라, 반도체 종합 서비스, 소재/모듈/리사이클링(Asset Lifecycle)
- Projects/awards: data centers, AI data centers, hyperscale, colocation, campus; Yongin cluster; fab; cleanroom; EPC/turnkey/JV; award/contract; groundbreaking/completion; schedule/cost
- Finance/IPO/PF: refinancing, CP/bonds, credit rating, PF, contingent liabilities, support obligations, guarantees, bridge loans, asset/stake sales, IPO/pre-IPO, valuation
- “Operations CEO lens”: yield/throughput/utilization/lead-time/change orders/risk mgmt; HBM/advanced packaging as background reference (not direct business unless evidenced)

3) SK ecoplant query set (KR/EN)
- CEO/governance/strategy
  ("SK에코플랜트" OR "SK ecoplant") AND ("김영식" OR "Youngsik Kim" OR "대표이사 사장")
  ("SK에코플랜트" OR "SK ecoplant") AND ("각자대표" OR "공동대표" OR "장동현")
  ("SK에코플랜트" OR "SK ecoplant") AND ("AI 인프라" OR "data center" OR "semiconductor infrastructure") AND (strategy OR "전략" OR "사업 재편")
- Awards/projects (core)
  ("SK에코플랜트" OR "SK ecoplant") AND (수주 OR 낙찰 OR 계약 OR EPC OR turnkey OR JV) AND (반도체 OR 클린룸 OR Fab OR "semiconductor")
  ("SK에코플랜트" OR "SK ecoplant") AND (수주 OR 계약 OR EPC OR turnkey) AND ("데이터센터" OR "data center" OR hyperscale OR colocation)
  (용인 OR "Yongin") AND (클러스터 OR cluster) AND (SK에코플랜트 OR SK ecoplant)
- Finance/PF risk (daily check)
  ("SK에코플랜트" OR "SK ecoplant") AND (차입 OR 차환 OR 유동성 OR "단기차입" OR 회사채 OR CP OR 금리)
  ("SK에코플랜트" OR "SK ecoplant") AND (PF OR 우발채무 OR "자금보충" OR 보증 OR "project finance")
  ("SK에코플랜트" OR "SK ecoplant") AND (지분매각 OR 자회사매각 OR "asset sale" OR "stake sale")
- IPO/capital markets
  ("SK에코플랜트" OR "SK ecoplant") AND (IPO OR 상장 OR "재추진" OR "pre-IPO" OR 밸류에이션)
  ("SK에코플랜트" OR "SK ecoplant") AND (신용등급 OR rating OR outlook OR "재무구조 개선")
- Competitive context
  (data center OR 데이터센터) AND (EPC OR contractor OR 수주) AND (Korea OR 국내 OR "APAC")
  (semiconductor fab OR 반도체 공장) AND (EPC OR cleanroom contractor OR 클린룸 시공) AND (award OR contract OR 수주)

SUMMARY CHECKLIST (enforced per article and per cluster)
- Fact: contract value/schedule/location/client/contractor/duration (with link + as-of date)
- Impact: order-mix, margin/cost/schedule risk, cashflow timing
- Risk: permitting/power/PF/refinancing/materials/inflation/change-order risk
- Next Signal: what to check next (filings, rating actions, follow-up milestones)

ANTI-HALLUCINATION / QUALITY RULES
- No claim without at least one source link.
- Separate Fact vs Inference sections.
- Numerical claims must store: value + currency/unit + as-of date + source + “claim-type”.
- Prefer official filings/PR for “hard facts”; treat rumors as low-confidence with explicit labeling.
- Must log which sources were used and show source-group distribution in output.

DELIVERABLES FOR THIS STAGE (Design + skeleton plan, NOT final production)
Provide:
1) Module architecture: collector / normalizer / clusterer / ranker / summarizer / formatter / store / ui / chat
2) DB schema draft (tables + key fields):
   - Article, Cluster, Briefing, SourceGroup, UserProfile(Stable Profile), ConversationHint
3) Diversity rules (quant constraints + recovery strategy if diversity is not met)
4) Scheduler job flow + idempotency strategy
5) Security architecture options (VPS+VPN-only focus) with tradeoffs
6) Formatter interface (HTML output spec) to later plug Opal or UI-generation AI/MCP
7) Decision points list (3–10 items) to finalize next

TONE
Use “recommend / candidate / option” language. Do not assume everything is fixed. Clearly list what is tentative.

END.
