# Agent Trading Company 계획서 (v0.1)

> 목적: **최대한 자율적인 LLM 에이전트**가 파일 기반으로 협업하며 한국투자증권 API를 통해 자동매매를 수행하는 시스템을 구축한다.
> 핵심: **모든 입력/출력/대화는 md 파일**, 에이전트는 **병렬 자율 실행**, 시스템은 **kill switch + 기록 강제**만 최소 불변 규칙으로 둔다.

---

## 0. 설계 원칙

1) **자율성 우선**
- 매매/리스크/평가/지표 산출까지 가능한 한 전부 에이전트가 판단한다.
- 시스템은 관측 가능성(무조건 파일로 남김)과 강제 종료(kill switch)만을 최소 불변 규칙으로 둔다.

2) **파일이 곧 인터페이스**
- 모든 입력/출력/대화는 **md 파일**로만 이루어진다.
- 에이전트 간 통신은 “상대 에이전트 폴더의 `jobs_todo/`에 job md 생성”으로만 수행한다.
- 각 에이전트 폴더 내의 `role.md`, `memory.md`는 **타 에이전트가 수정하지 않는다**.

3) **병렬 + 이벤트 기반**
- 중앙에서 순차 실행하지 않는다.
- 각 에이전트는 자신의 `jobs_todo/`를 감시하고 새 job이 생기면 자율적으로 처리한다.

4) **외부 기능은 Skills로 캡슐화**
- 인터넷 검색/파이썬 분석/한국투자증권 API 호출은 스킬로 제공한다.
- 에이전트는 필요 시 스킬 설명(md)을 읽고 런타임을 통해 실행한다.
- 스킬 구조는 Codex/Claude Skills 문서를 참고한다.
  - https://developers.openai.com/codex/skills
  - https://code.claude.com/docs/ko/skills

---

## 1. 요구사항 반영(확정 사항)

### 1-a. 목표/범위/금지룰은 파일로 저장
- 범위/금지룰(예: 레버리지/공매도/파생 미사용)은 `admin/charter.md`에 기록한다.
- 목표는 반드시 고정하지 않는다.
  - `admin/objectives.md`는 **선택 파일**로 둔다.
  - 비어 있으면 에이전트가 스스로 목표를 세우고 그 근거를 산출물(md)에 남긴다.

### 1-b. 실행도 에이전트가 수행
- 주문 실행(실전/모의), 계좌/잔고/포지션 파악은 에이전트가 스킬을 통해 수행한다.
- 시스템은 실행을 “막지 않는다”. 단, kill switch는 강제한다.

### 1-c. 데이터 품질/분석은 분석 에이전트가 자율 판단
- 어떤 데이터를 수집할지, 필요/불필요 판단, 파이썬 분석/그래프 생성 여부는 분석(또는 해당 역할) 에이전트가 결정한다.
- 시스템은 “원본/결과 md가 남는 것”만 강제한다.

### 1-d. jobs_todo → jobs_complete 작업 흐름
- 작업 결과물을 생성하면 수신자를 정해 해당 에이전트의 `jobs_todo/`에 job md를 생성한다.
- 완료된 job은 `jobs_complete/`로 이동한다.
- 충돌 최소화를 위해 **클레임(Claim) 이동 규칙**을 권장한다.
  - 처리 시작: `jobs_todo/` → `jobs_doing/` (원자적 rename)
  - 처리 완료: `jobs_doing/` → `jobs_complete/`

### 1-e. 리스크 관리는 리스크 에이전트가 수행, 상호작용으로 조정
- 리스크 에이전트는 trader에게 경고/권고/벌점 제안 등을 job으로 전달한다.
- trader는 이를 읽고 **자율적으로** 행동을 조정하거나 반박할 수 있다.
- 강제 리스크 규칙은 두지 않는다(요청사항).
- 단, 에이전트 단위 kill switch는 반드시 제공한다.

### 1-f. 프롬프트 백업(직전/전전)
- 각 에이전트는 실행 시 사용된 프롬프트 구성 요소를 md로 보관한다.
- 최소: `prompt_last.md` + `prompt_prev.md` 유지.

### 1-g. 모든 행동은 결과물(md) 필수
- 성공/실패와 무관하게 반드시 결과 md를 남긴다.
- 결과 md에는 최소한 다음이 포함된다.
  - 무엇을 시도했는지
  - 입력 refs
  - 결과/실패 원인
  - 후속 조치(필요 시 job 생성)

---

## 2. 시스템 구성(최소)

### 2.1 Agent Runtime(런타임)
- 런타임은 “결정”을 하지 않는다.
- 역할:
  - 각 에이전트 `jobs_todo/` 감시
  - kill switch 감지
  - job 클레임(doing 이동)
  - 모델 라우팅 적용 후 에이전트 호출
  - 결과 md 생성 여부 확인
  - job 완료 이동(complete)
  - 런타임 로그 append

### 2.2 파일 기반 이벤트 흐름
- 작업 결과물 생성 → 수신자 결정 → 수신자 `jobs_todo/`에 job md 생성
- 에이전트는 job 읽고 처리 → 결과 md 생성 → job을 `jobs_complete/`로 이동
- 피드백/추가 요청도 job md로 전달

---

## 3. 디렉터리/파일 규약(MVP 핵심만)

### 3-a. 최소 디렉터리
```
/admin/
  charter.md
  broadcast.md
  models.md
  KILL_ALL

/agents/
  /collector/
    role.md
    memory.md
    prompt_last.md
    prompt_prev.md
    jobs_todo/
    jobs_doing/
    jobs_complete/
    outputs/
    KILL
  /trader/
    ... (동일)
  /risk/
    ... (동일)

/skills/
  /web_search/SKILL.md
  /python_run/SKILL.md
  /kis_api/SKILL.md
  index.md

/logs/
  runtime.md
```

> MVP에서는 `/artifacts/` 같은 중앙 저장소 없이 각 에이전트의 `outputs/`만으로 시작해도 된다.

### 3-b. 프롬프트 구성 순서(고정)
1) `admin/charter.md` (불변/준불변 룰)
2) `agents/<name>/role.md` (역할/출력 형식/금지행동)
3) `admin/broadcast.md` (전사 공지)
4) `agents/<name>/memory.md` (짧은 메모리)
5) `skills/index.md` + 허용 스킬 요약
6) 이번 job md (`jobs_doing/<job>.md`)
7) 실행 규약(결과 md 생성, 후속 job 생성, prompt 백업)

### 3-c. 모든 파일은 md + 최소 메타데이터
- 모든 md는 상단에 YAML front matter를 둘 수 있다(권장).
- 필드는 최소로 유지한다.

#### Job md 예시
```md
---
job_id: JOB-20260131-123045
from: trader
to: risk
created_at: 2026-01-31T12:30:45+09:00
refs:
  - agents/trader/outputs/DECISION-20260131-122900.md
---

요청:
- 위 decision을 기준으로 현재 계좌/포지션을 확인하고,
- 리스크 관점에서 문제점/권고사항을 작성해 주세요.
- 반드시 결과 파일을 outputs/에 남기고, 필요한 후속 job이 있으면 생성해 주세요.
```

#### 결과 md 예시
```md
---
artifact_id: RESULT-20260131-123300
agent: risk
status: success  # or fail
created_at: 2026-01-31T12:33:00+09:00
refs:
  - agents/trader/outputs/DECISION-20260131-122900.md
---

핵심 결론:
- (자율 서술)

근거/관찰:
- (자율 서술)

권고/요청:
- (필요 시 trader에게 새 job 생성)
```

---

## 4. Skills 설계(MVP)

### 4.1 스킬 구성
- `/skills/<skill_name>/SKILL.md` 단일 파일을 기준으로 구성한다.
- 에이전트 프롬프트에는 “허용 스킬 목록/요약”만 포함하고, 필요 시 해당 스킬 md를 참조하도록 한다.

### 4.2 MVP 스킬 3개
1) `web_search` : 뉴스/공시/일반 웹 검색
2) `python_run` : 데이터 파일 기반 분석/그래프 생성(결과는 md 요약)
3) `kis_api` : 한국투자증권 시세/잔고/주문

---

## 5. 모델 라우터(에이전트별 모델 선택)

- `admin/models.md`에 에이전트별 provider/model 매핑을 둔다.
- 비용 계산/캐시/메모리 최적화는 MVP에서 필수 아님(요청사항).
- 단, 구조적으로 확장 가능하도록 파일 기반 설정만 둔다.

예시: `admin/models.md`
```md
---
updated_at: 2026-01-31T00:00:00+09:00
---

collector: openai:gpt-4.1-mini
trader: openai:gpt-4.1
risk: openai:gpt-4.1
```

---

## 6. 한국투자증권 API 연동 계획(모의/실전)

- `kis_api` 스킬에서 KIS 인증/토큰/시세/주문 기능을 제공한다.
- 모의/실전은 KIS 공식 문서/예제에서 안내하는 전환 방식(도메인/설정 값 변경)을 따른다.

개발 가이드(계획서용):
1) KIS 개발자 포털에서 앱 등록 및 키 발급
2) 공식 문서/예제 기준으로 인증/토큰 로직 구현
3) 모의투자에서 먼저 검증 후 실전 전환

참고:
- https://apiportal.koreainvestment.com/
- https://github.com/koreainvestment/open-trading-api

---

## 7. 에이전트 정의(MVP 최소)

### 7.1 Collector Agent
- 역할: 시장 데이터/현재가/호가/관심 종목 스냅샷 수집
- 스킬: `kis_api`, 필요 시 `web_search`
- 산출물: `outputs/SNAPSHOT-*.md`
- 후속: trader(또는 analyst)에 job 생성

### 7.2 Trader Agent
- 역할: 수집/리스크 피드백을 읽고 매수/매도/홀드를 자율 판단하고 실행 가능
- 스킬: `kis_api`, 필요 시 `python_run`, `web_search`
- 산출물:
  - `outputs/DECISION-*.md`
  - `outputs/ORDER-*.md` (주문 요청/응답 요약)
- 후속: risk에게 검토 요청 job 생성 가능

### 7.3 Risk Agent
- 역할: 계좌/포지션 점검, 리스크 관점 권고/경고/벌점 제안
- 스킬: `kis_api`, 필요 시 `python_run`
- 산출물: `outputs/RISK-*.md`
- 후속: trader에게 조정 요청 job 생성

> Analyst Agent는 MVP에서 생략 가능. 필요하면 4번째로 추가.

---

## 8. Kill Switch 설계

- 전체 중단: `admin/KILL_ALL` 파일이 존재하면 런타임은 모든 에이전트를 중지한다.
- 개별 중단: `agents/<name>/KILL` 파일이 존재하면 해당 에이전트만 중지한다.
- 중단 시에도 `outputs/STOP-*.md` 결과물을 남긴다.

---

## 9. 실행 규약(런타임 ↔ 에이전트 최소 계약)

### 9.1 런타임 규약
- job 클레임: `jobs_todo/` → `jobs_doing/` (원자적 rename)
- 에이전트 호출 후, 다음을 확인한다.
  - 결과 md 생성 여부(필수)
- 완료 처리: `jobs_doing/` → `jobs_complete/`
- 프롬프트 백업:
  - `prompt_prev.md` ← `prompt_last.md`
  - `prompt_last.md` 갱신
- 로그 append: `/logs/runtime.md`

### 9.2 에이전트 규약
- 입력 job을 읽고 자율 판단
- 필수:
  1) 결과 md를 `outputs/`에 생성(성공/실패 모두)
  2) 필요 시 타 에이전트에 후속 job 생성
  3) (선택) `memory.md`를 짧게 갱신

---

## 10. MVP 실행 시나리오(최소 루프)

1) 관리자가 `admin/charter.md`에 금지룰(레버리지/공매도/파생 금지)과 기록/kill 규칙만 작성
2) Collector가 KIS로 관심 종목 현재가/호가 1회 수집 → `SNAPSHOT-*.md` 저장
3) Collector가 trader에게 job 생성
4) Trader가 스냅샷을 읽고 자율 결정 → `DECISION-*.md` 저장
5) Trader가 risk에게 검토 job 생성
6) Risk가 계좌/포지션 점검 및 권고 → `RISK-*.md` 저장, trader에게 피드백 job 생성
7) Trader가 피드백을 반영(또는 반박)하고 모의투자로 주문 실행 → `ORDER-*.md` 저장
8) 모든 단계가 md로 누적되는지 확인

---

## 부록 A. admin 파일 템플릿

### `admin/charter.md`
```md
---
updated_at: 2026-01-31T00:00:00+09:00
---

불변 룰:
- 레버리지 사용 금지
- 공매도 금지
- 파생상품 거래 금지
- 모든 행동은 md 결과물을 남긴다(성공/실패 포함)
- kill switch 파일이 존재하면 즉시 중단한다
```

### `admin/broadcast.md`
```md
---
updated_at: 2026-01-31T00:00:00+09:00
---

전사 공지:
- (관리자가 전체 에이전트 프롬프트에 넣고 싶은 지시를 여기에 작성)
```

---

## 부록 B. 에이전트 role.md 템플릿

### `agents/trader/role.md`
```md
---
agent: trader
---

당신은 자동매매 회사의 매매 담당입니다.
입력(job)과 이전 산출물을 읽고, 자율적으로 매수/매도/홀드를 결정하고 실행할 수 있습니다.

필수:
- 매 행동마다 outputs/에 결과 md를 남길 것(성공/실패 모두)
- 필요 시 risk에게 확인/피드백 job을 보낼 것
- prompt_last.md, prompt_prev.md 백업 규약을 준수할 것

산출물:
- DECISION-*.md : 결정/근거/요청
- ORDER-*.md : 주문 요청/응답 요약(모의/실전 구분 포함)
```

