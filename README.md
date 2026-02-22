# News Agent — 가족 내부용 임원 뉴스 브리핑 에이전트

매일 아침, 반도체 Fab · 데이터센터 · 건설/수주 · 투자/정책 분야의 핵심 뉴스를
자동 수집 → 클러스터링 → 요약하여 **5~20분 브리핑**으로 제공하는 시스템.

## 핵심 특징

- **2트랙 출력**: 정확성 중심 텍스트 브리프 + 모바일 친화 HTML 카드 브리프
- **편향 억제**: Stable Profile(고정 관심사) 기반, 소스 다양성 강제, Fact/Inference 분리
- **SK에코플랜트 관전 오버레이**: 수주믹스, 재무/차입, PF 우발, IPO 시그널 매일 체크
- **가족 전용**: VPS + VPN-only 접근, 멀티테넌트/공개 배포 고려 없음

## 로드맵

1. **Program #1** — ChatGPT Export Analyzer (Stable Profile 추출)
2. 초기 스코프/렌즈 결합
3. 뉴스 수집 파이프라인 설계/구현
4. 요약 + HTML 브리핑 생성
5. 1~2주 튜닝

## Tech Stack

- Python (CLI → FastAPI)
- SQLite (→ 추후 필요 시 확장)
- LLM 호출 플러그형 (모델 미확정)

## Getting Started

```bash
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

## Project Structure

```
News_Agent/
├── README.md
├── .gitignore
├── requirements.txt          # (추후 생성)
├── docs/
│   └── initial_design/       # GPT와 사전 논의한 설계 문서 원본
└── src/                      # (추후 생성)
```
