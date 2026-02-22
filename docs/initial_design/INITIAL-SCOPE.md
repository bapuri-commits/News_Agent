# 초기 스코프 세트 (키워드 / 쿼리 / 소스군) + SK에코플랜트(김영식 CEO 관전) 튜닝 통합본

> 목적: (1) 산업 전반 동향(반도체 Fab/DC/건설/투자) + (2) SK에코플랜트/김영식 체제 관전(수주·재무·PF·IPO)  
> 원칙: **소스/관점 다양성 강제**, 대화 컨텍스트는 **얕게(5~10%)**만 반영

---

## A) 핵심 토픽 트리 (4대 축 → 12개 서브스코프)

### [A. 반도체 Fab / 공급망 / CapEx]
- **A1. Fab 신·증설 / CapEx / 일정** (groundbreaking, ramp, delay)
- **A2. 클린룸 / 공정 인프라** (UPW, CDA, 케미컬, 가스, 배기/스크러버)
- **A3. 장비·부품 공급망** (ASML, AMAT, Lam, TEL / 밸브·펌프·케미컬)
- **A4. 첨단 패키징** (advanced packaging, CoWoS, HBM line, OSAT)

### [B. 데이터센터 / AI 인프라]
- **B1. 하이퍼스케일·코로케이션 신축/캠퍼스** (용량 MW, 부지, 임차)
- **B2. 전력** (utility interconnection, PPA, substation, grid constraint)
- **B3. 냉각** (액침/수랭, CDU, 열밀도, 규제/환경)
- **B4. 네트워크/클라우드** (주요 사업자 투자/리전/연기)

### [C. 건설·수주·프로젝트 리스크]
- **C1. EPC/GC 수주·JV·하도급 구조, 공기/원가 리스크**
- **C2. 인허가/환경/지역 반발** (특히 DC)
- **C3. 안전/품질/컴플라이언스** (위험물, 클린룸 기준)
- **C4. 자재/노무/장비 수급** (가격/리드타임)

### [D. 투자/정책/시장 사이클]
- **D1. 정부정책** (보조금, CHIPS류, 세제, 규제)
- **D2. 기업 투자 가이던스** (CapEx 전망, 감산/증산)
- **D3. 금융** (프로젝트 파이낸스, 리파이낸싱, CMBS 등)
- **D4. IPO/기업가치 관점** (건설사/인프라 개발사/운영사)

---

## B) 키워드 세트 (KR/EN 혼합, 처음엔 넓게)

### [회사/플레이어]
- (반도체) **TSMC, Samsung, SK hynix, Intel, Micron, GlobalFoundries, Texas Instruments, UMC, SMIC**
- (DC) **AWS, Microsoft, Google, Oracle, Meta, Equinix, Digital Realty, QTS, CyrusOne, Switch, NTT, GDS**
- (장비/인프라) **ASML, Applied Materials, Lam, TEL, KLA / Schneider, Vertiv, Eaton, ABB, Siemens, Legrand**

### [Fab 쪽 키워드]
- KR: 팹 증설, 라인 증설, 클린룸, 공정 인프라, 초순수(UPW), 케미컬 공급, 스크러버, 배기, 가스/케미컬 안전, 첨단패키징, HBM
- EN: fab expansion, capex, cleanroom, UPW, CDA, abatement, scrubber, specialty gases, advanced packaging, HBM line, ramp, delay

### [DC 쪽 키워드]
- KR: 데이터센터 신축, 캠퍼스, 하이퍼스케일, 코로케이션, 변전소, 계통연계, 전력부족, PPA, 수랭/액침냉각, MW, 열밀도
- EN: data center campus, hyperscale, colocation, utility interconnection, substation, grid constraint, PPA, liquid cooling, immersion cooling, MW capacity

### [투자/정책 키워드]
- KR: 보조금, 세제혜택, 규제, 인허가, 프로젝트 파이낸스, 리파이낸싱, CMBS, CapEx 전망, IPO
- EN: subsidies, tax credits, permitting, project finance, refinancing, CMBS, capex guidance, IPO

---

## C) 쿼리 템플릿 (실제 수집 검색어 조합 규칙)

> 운영: 서브스코프별 템플릿을 돌려 **매일 30~200개 문서 풀** 수집 → **클러스터링/중복제거** → 최종 20~40개 노출

### Fab/CapEx
- `(<회사명> OR <지역>) AND (fab OR semiconductor plant OR cleanroom) AND (capex OR expansion OR construction OR groundbreaking OR ramp OR delay)`
- `(advanced packaging OR HBM line) AND (investment OR capacity OR equipment)`

### DC/전력
- `(data center campus OR hyperscale OR colocation) AND (MW OR capacity) AND (<지역> OR <회사>)`
- `(utility interconnection OR substation OR grid constraint OR PPA) AND data center`

### 건설/수주
- `(EPC OR contractor OR JV OR procurement) AND (data center OR semiconductor) AND (award OR contract OR tender)`
- `(permitting OR zoning OR environmental) AND data center AND (<지역>)`

### 투자/금융
- `(refinancing OR CMBS OR project finance) AND data center`
- `(capex guidance OR earnings call) AND (semiconductor OR data center)`

---

## D) 소스군(출처) 세트 (편향 억제를 위해 군집화)

- **S1. 데이터센터 전문**: DatacenterDynamics(DCD)
- **S2. 반도체 전문**: EE Times (+ 후보: Semiconductor Engineering, SEMI, SIA)
- **S3. 기업 공식/공시/프레스룸**: 기업 PR/IR/공시(예: TSMC PR)
- **S4. 컨설팅/리서치**: McKinsey(DC/반도체), SIA 연간리포트 등
- **S5. 건설 산업 전문**: ENR(+ 후보: 지역 ENR, 공공 발주/입찰 DB)
- **S6. 종합 경제지(균형)**: FT/WSJ/Reuters/Bloomberg/Nikkei 등
- **S7. 국내(한국어)**: 연합뉴스/한경/매경/조선비즈/전자신문/더일렉/더벨/공공기관 공지·입찰

> 운영 팁: 매일 결과물에 **소스군 분포** 표기 (예: S1 4개, S2 4개, S5 2개, S6 3개…)  
> 국내는 “수주/정책/인허가/전력” 로컬 이슈, 해외는 “메가 트렌드/투자 사이클” 보완.

---

# SK에코플랜트(김영식 CEO 관전) 스코프 튜닝 통합

## 1) 관전 축(뉴스를 읽는 렌즈) — 요약 포맷에 고정 삽입
- **수주·믹스 변화**: 반도체/AI 인프라 비중 실제 상승 여부
- **현금흐름·차입 구조**: 단기물 비중, 차환/금리, 유동성 이벤트
- **PF 우발/리스크**: 자금보충약정/우발채무/프로젝트 리스크 축소 여부
- **IPO·포트폴리오 정리**: 자회사/지분 매각, 사업구조 재편, 상장 신호

---

## 2) 엔티티(고정 키워드)

### [핵심 엔티티]
- 김영식, 장동현, 각자대표, 대표이사 사장, 대표이사 부회장
- SK에코플랜트, SK ecoplant
- AI 인프라 밸류체인, 반도체 인프라, 반도체 종합 서비스, 소재/모듈/리사이클링(Asset Lifecycle)

### [프로젝트·수주 맥락]
- 데이터센터, AI 데이터센터, 하이퍼스케일, 코로케이션, 캠퍼스
- 반도체 클러스터, 용인 클러스터(Yongin cluster), 팹(Fab), 클린룸
- EPC, 턴키, JV, 수주, 낙찰, 계약, 착공, 준공, 공기, 원가

### [재무·IPO·리스크 맥락]
- 총차입금(6조대), 단기차입(60% 내외), 부채비율(200%대)
  - **주의**: 숫자는 “주장(Claim)”으로 저장하고 **기사 근거/기준시점**을 함께 기록
- 차환, 유동성, 금리, 회사채, CP, 신용등급, 리파이낸싱
- PF, 우발채무, 자금보충약정, 보증, 브릿지론
- 지분 매각, 자회사 매각, 현금 확보, 구조조정, 포트폴리오 정리
- IPO, 상장 재추진, 밸류에이션, 프리IPO, 투자유치

### [반도체 운영형 CEO 렌즈]
- 제조/기술, 양산, 수율, 가동률, 납기, 변경관리(체인지 오더), 리스크 관리
- HBM, advanced packaging(첨단패키징)
  - **용도**: 직접 사업이라기보다 CEO 강점/레퍼런스(해석 파트)로 반영

---

## 3) 쿼리 세트(검색/수집 파이프라인용, KR/EN)

### (1) CEO/지배구조/전략 시그널
- `("SK에코플랜트" OR "SK ecoplant") AND ("김영식" OR "Youngsik Kim" OR "대표이사 사장")`
- `("SK에코플랜트" OR "SK ecoplant") AND ("각자대표" OR "공동대표" OR "장동현")`
- `("SK에코플랜트" OR "SK ecoplant") AND ("AI 인프라" OR "data center" OR "semiconductor infrastructure") AND (strategy OR "전략" OR "사업 재편")`

### (2) 수주/프로젝트(반도체·DC) — 핵심
- `("SK에코플랜트" OR "SK ecoplant") AND (수주 OR 낙찰 OR 계약 OR EPC OR turnkey OR JV) AND (반도체 OR 클린룸 OR Fab OR "semiconductor")`
- `("SK에코플랜트" OR "SK ecoplant") AND (수주 OR 계약 OR EPC OR turnkey) AND ("데이터센터" OR "data center" OR hyperscale OR colocation)`
- `(용인 OR "Yongin") AND (클러스터 OR cluster) AND (SK에코플랜트 OR SK ecoplant)`

### (3) 재무/차입/차환/리스크(IPO 전제) — 매일 체크
- `("SK에코플랜트" OR "SK ecoplant") AND (차입 OR 차환 OR 유동성 OR "단기차입" OR 회사채 OR CP OR 금리)`
- `("SK에코플랜트" OR "SK ecoplant") AND (PF OR 우발채무 OR "자금보충" OR 보증 OR "project finance")`
- `("SK에코플랜트" OR "SK ecoplant") AND (지분매각 OR 자회사매각 OR "asset sale" OR "stake sale")`

### (4) IPO/자본시장 신호
- `("SK에코플랜트" OR "SK ecoplant") AND (IPO OR 상장 OR "재추진" OR "pre-IPO" OR 밸류에이션)`
- `("SK에코플랜트" OR "SK ecoplant") AND (신용등급 OR rating OR outlook OR "재무구조 개선")`

### (5) 경쟁/비교(시야 확보)
- `(data center OR 데이터센터) AND (EPC OR contractor OR 수주) AND (Korea OR 국내 OR "APAC")`
- `(semiconductor fab OR 반도체 공장) AND (EPC OR cleanroom contractor OR 클린룸 시공) AND (award OR contract OR 수주)`

> 운영 팁: 위 쿼리로 “수집 풀” 생성 → 사건(클러스터) 기준 **20~40개로 압축**해 최종 노출.

---

## 4) 요약 체크리스트(임원 브리핑 강제 포맷)

- **Fact(확인된 내용)**: 계약/금액/일정/프로젝트 위치/발주처/수주자/공기
- **Impact(회사에 미치는 의미)**: 수주믹스, 수익성(원가/공기 리스크), 현금흐름 타이밍
- **Risk(리스크)**: 인허가/전력/PF/차환/원가상승/변경관리
- **Next Signal(내일/다음주 확인할 것)**: 후속 공시, 신용등급 변화, 추가 매각 루머, 프로젝트 진행률
