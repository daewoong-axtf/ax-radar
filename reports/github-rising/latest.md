# 11월 넷째 주 GitHub 별 급상승 AI·개발 도구 BEST 10

TOP 시리즈 · 2026-11-23

> 집계 기간: 2026-11-16 15:08 ~ 2026-11-23 15:08 (KST). GitHub API로 별 수를 직접 세서 만든 순위예요. GitHub 공식 트렌딩 순위가 아니에요.
> `≈`는 추정치예요. 7일 전 기록이 없어서 공개 GH Archive 표본으로 세고, 이번 주 새로 생긴 저장소로 비율을 맞춰 전체 별 수로 환산했어요. 순서는 믿을 만하지만 숫자는 ±25% 정도 차이 날 수 있어요.

| 순위 | 저장소 | 별 증가 | 지난주 대비 | 라이선스 | 한 줄 | 단, 확인할 것 |
|---|---|---|---|---|---|---|
| 1 | [morluto/rea](https://github.com/morluto/rea) | ≈+14,300 | 지난주 1위 = | MIT | 바이너리·앱 동작까지 에이전트로 역공학하는 MCP 도구 | 분석할 권한이 있는 앱·바이너리에만 쓰세요 |
| 2 | [elementalsouls/Claude-BugHunter](https://github.com/elementalsouls/Claude-BugHunter) | ≈+12,200 | 새로 진입 | MIT | Claude Code를 버그 바운티·레드팀 연구자처럼 쓰게 해 주는 보안 스킬 묶음 (83개) | 허가받은 대상에만 쓰세요. 후원사가 있는 개인 프로젝트예요 |
| 3 | [BaaRai/ARTEX](https://github.com/BaaRai/ARTEX) | ≈+12,200 | 새로 진입 | AGPL-3.0 | 여러 에이전트가 실제 도구로 침투 테스트를 하고 증거를 남기는 자체 호스팅 플랫폼 | 허가받은 대상에만 쓰세요. 원본(Autumn-27/ARTEX)을 가져온 저장소이고 AGPL-3.0이에요 (README) |
| 4 | [pingdotgg/t3code](https://github.com/pingdotgg/t3code) | ≈+11,200 | 지난주 4위 = | MIT | Claude Code·Codex 등 내 컴퓨터의 코딩 에이전트를 한 화면과 휴대폰에서 조종하는 앱 | 에이전트가 먼저 내 컴퓨터에 설치·로그인돼 있어야 해요 (README) |
| 5 | [Ebony-Vinyl/dsh-our-free-model](https://github.com/Ebony-Vinyl/dsh-our-free-model) | ≈+10,300 | 지난주 3위 ▼2 | - | DeepSeek Harness(dsh)에 붙이면 로그인·API 키 없이 여러 최신 모델을 무료로 쓰게 해 주는 플러그인 | 베타예요. 출처가 불분명한 무료 모델 중계라 이용약관·데이터 유출 위험을 먼저 확인하세요 · 라이선스 표기 없음 |
| 6 | [stablyai/orca](https://github.com/stablyai/orca) | ≈+9,600 | 지난주 9위 ▲3 | MIT | 코딩 에이전트 여러 개를 한 IDE에서 동시에 돌리고 Slack·휴대폰에서 지시하는 앱 | Claude Code나 Codex는 직접 준비해야 해요 |
| 7 | [erkamyaman/rust-anything](https://github.com/erkamyaman/rust-anything) | +8,155 | 새로 진입 | MIT | 앱을 조각조각 Rust로 옮기고, 원본과 똑같이 동작하는지 기록으로 검증하는 도구 | Rust 코드는 내 코딩 에이전트(Claude Code 등)가 써요. PHP·C#은 함수 단위 포팅만 돼요 (README) |
| 8 | [obra/superpowers](https://github.com/obra/superpowers) | ≈+7,300 | 새로 진입 | MIT | 코딩 에이전트가 요구사항 정리, 설계, 계획, TDD, 리뷰 순서로 일하게 만드는 스킬 모음 | 에이전트가 몇 시간씩 혼자 작업할 수 있어서 토큰 사용량을 지켜보세요. 시각 도구에는 원격 측정이 있어요 (README) |
| 9 | [mdiri-ai/SoduWork](https://github.com/mdiri-ai/SoduWork) | ≈+6,841 | 새로 진입 | MIT | 팀과 에이전트가 요청을 주고받고 요청자 승인까지 관리하는 자체 호스팅 업무 엔진 | 여러 에이전트 하네스를 지원하지만 직접 설치·실행해야 해요. Python 3.12·Node 22 권장 (README) |
| 10 | [nexu-io/openmotion](https://github.com/nexu-io/openmotion) | ≈+6,100 | 새로 진입 | Apache-2.0 | Claude Motion·CapCut 대안으로, 에이전트가 모션 그래픽 영상을 만들게 하는 오픈소스 도구 | Node.js 22.18 이상이 필요해요 (README) |

## 바로 써 보기 (설치 한 줄)

**1위 morluto/rea**

```bash
npx rea-agents setup
```

**2위 elementalsouls/Claude-BugHunter**

```bash
/plugin marketplace add elementalsouls/Claude-BugHunter
```

**3위 BaaRai/ARTEX**

```bash
git clone https://github.com/BaaRai/ARTEX.git && cd ARTEX && docker compose up -d --build
```

**4위 pingdotgg/t3code**

```bash
curl -fsSL https://t3.codes/install.sh | sh
```

**5위 Ebony-Vinyl/dsh-our-free-model**

```bash
dsh plugin --profile web add <내려받은 폴더 경로>
```


## 빠진 곳

- [meta/astryx](https://github.com/meta/astryx) · 지난주 2위 (이번 주 +5,000)
- [janestreet/agent_skills](https://github.com/janestreet/agent_skills) · 지난주 5위 (이번 주 +1,300)
- [ccch1mneyyy/dsh-Go](https://github.com/ccch1mneyyy/dsh-Go) · 지난주 6위 (이번 주 +5,900)
- [yetone/magpie](https://github.com/yetone/magpie) · 지난주 7위 (이번 주 +3,500)
- [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) · 지난주 8위 (이번 주 +4,300)
- [vercel-labs/ui](https://github.com/vercel-labs/ui) · 지난주 10위 (이번 주 +1,900)

## 출처

- GitHub REST API: 검색(`/search/repositories`), 저장소 정보(`/repos`), 별 기록(`/repos/{owner}/{repo}/stargazers`)
- 후보 765개 중 별 증가 순. 필터: 포크 5개 이상, AI 관련 키워드
