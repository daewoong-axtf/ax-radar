# ax-radar

AI·개발 동향을 여러 소스에서 모아서 **Slack / Discord / RSS / 웹훅**으로 알려 주는 봇이에요.
서버 없이 GitHub Actions만으로 돌아가요. 소스는 하나씩 붙여 나가는 구조예요.

| 소스 | 주기 | 내용 | 상태 |
|---|---|---|---|
| `github_rising` | 매주 월 07:00 KST (스냅샷은 매일 06:00) | 지난 7일 GitHub 별 급상승 AI·개발 도구 BEST 10 | ✅ |
| arXiv / HF Daily Papers, GeekNews, HN, 공식 블로그 | 매일 아침 | 소스 조사 완료, 구현 예정 | 예정 |

## 구조

```
radar/
  __main__.py          CLI: python -m radar <소스> <명령>. SOURCES에 소스를 등록해요
  github.py            GitHub REST 클라이언트 (재시도, 한도 대기)
  notify.py            Slack / Discord / 웹훅 전송 (모든 소스 공통)
  site.py              GitHub Pages 공통 레이아웃
  summarize.py         API 키로 한국어 요약 (mode=api일 때만)
  sources/
    github_rising/     소스 하나 = 폴더 하나. COMMANDS 와 run() 만 있으면 돼요
data/<소스>/           수집 기록 (Actions가 자동 커밋)
reports/<소스>/        사람이 읽는 Markdown 리포트
public/                GitHub Pages 사이트 + RSS (Actions가 매번 만들어 배포, 커밋 안 함)
config.toml            공통 [summary] [notify] + 소스별 [<소스>.*]
```

## github_rising: GitHub 별 급상승

```
매일 06:00 KST    snapshot  후보 약 1,500개의 별 수 → data/github_rising/snapshots/날짜.json
월요일 07:00 KST  report    7일 전과 비교 → BEST 10 저장, 페이지 갱신 (알림은 잠깐 보류)
월요일 08:40 KST  Claude 예약 작업이 README를 읽고 한국어 요약·범위 확인 후 push (API 키 불필요)
        push 직후  publish   웹페이지 · RSS · Slack · Discord · 웹훅 발송
월요일 11:00 KST  publish   요약이 안 왔으면 저장소 설명만으로 발송 (이미 보냈으면 건너뜀)
```

웹페이지: https://daewoong-axtf.github.io/ax-radar/ (RSS: `/github-rising/feed.xml`)

### 순위는 이렇게 정해요

한 줄로: **AI/LLM·개발 도구 저장소 중에서, 지난 7일 동안 GitHub 별이 가장 많이 늘어난 10개**예요.
GitHub 공식 Trending 순위가 아니라, 별 수를 직접 세서 매긴 순위라서 Trending 순서와 다를 수 있어요.

**① 후보 모으기 (매일 06:00, 넓게)**

| 출처 | 내용 |
|---|---|
| 새로 생긴 인기 저장소 | 최근 30일 안에 생기고 별 150개 넘은 것, 최근 90일 안에 생기고 별 800개 넘은 것 |
| AI 토픽 검색 (약 30개) | `ai-agents` `agents` `agentic-ai` `multi-agent` `agent-skills` `skills` `llm` `mcp` `model-context-protocol` `mcp-server` `claude-code` `codex` `cursor` `copilot` `coding-agent` `ai-coding` `rag` `vector-database` `embeddings` `prompt-engineering` `context-engineering` `llmops` `evals` `ai-observability` `local-llm` `ollama` `inference` `generative-ai` `ai`(별 3천 이상). 지난 7일 안에 업데이트된 것만, 토픽마다 별 많은 순 100개 |
| [GitHub Trending](https://github.com/trending) | 일간·주간 × 전체·Python·TypeScript·JavaScript·Rust·Go 페이지에 오른 저장소 |
| 계속 추적 | 한 번 후보가 된 저장소는 35일 동안 매일 별 수를 기록해요 |

매일 기록하는 이유: 7일 전 별 수가 있어야 정확한 증가량을 셀 수 있어서예요. GitHub는 별 누른 기록을 외부에 보여 주지 않아요.
기록은 `data/github_rising/snapshots/날짜.json`에 쌓여요. 검색어와 Trending 설정은 `config.toml`의 `[github_rising.discovery]`에 있어요.

**② 순위에 올릴 수 있는 저장소 (자격)**

- 포크나 보관(archived) 저장소가 아니에요.
- 별 100개 이상, 포크 5개 이상이에요. 포크가 거의 없는 저장소는 별을 사서 올린 경우가 많아서 빼요.
- 이름·설명·토픽에 AI 관련 단어가 있어요 (`ai`, `agent`, `llm`, `claude`, `mcp`, `rag`, `codex` 등. 전체 목록은 `[github_rising.filter].keywords`).
- `[github_rising.filter].exclude`에 직접 넣은 저장소가 아니에요.

**③ 주제 범위: AI/LLM과 개발 도구만**

수집은 넓게 하고, 순위에 올릴 때만 주제를 봐요.

| 올려요 | 빼요 ("제외한 곳"에 이유와 함께 표시) |
|---|---|
| **AI/LLM**: 모델, AI 에이전트·프레임워크, MCP 서버, 에이전트 스킬, RAG, 프롬프트·컨텍스트 도구, 로컬 LLM 실행기, 평가·운영 도구 | **창작·디자인 도구**: 블렌더 애드온 등 |
| **개발 도구**: 코딩 에이전트(Claude Code·Codex·Cursor 관련), CLI, 에디터 확장, UI 라이브러리, 개발 생산성 도구 | **게임·일반 사용자용 앱** |
| | **강의·자료·링크 모음**: 강의 자료, 면접 문제, awesome 목록 등 |
| | **주제와 무관한 화제성 저장소** |

두 단계로 걸러요.
1. 규칙: 이름·토픽·설명에 위 "빼요" 단어가 있으면 자동으로 빼요 (`[github_rising.scope]`의 `rules`).
2. Claude 확인: 매주 예약 작업이 Top 10과 예비 10개의 README를 읽고, 범위 밖이면 빼요. 빈자리는 다음 순위 저장소로 채워요. 애매하면 빼지 않아요.

MCP 서버와 에이전트 스킬은 대상이 창작 도구나 앱이어도 올려요 (예: 블렌더용 MCP 서버). 빼고 싶지 않은 저장소는 `[github_rising.scope].include`에 넣으면 돼요.

**④ 순서 정하기**

- **오늘 별 수 − 7일 전 별 수**가 큰 순서예요. 같으면 전체 별 수가 많은 쪽이 앞이에요.
- 이번 주에 생긴 저장소는 전체 별 수가 곧 증가량이에요.
- 7일 전 기록이 없을 때(첫 주)는 공개 이벤트 기록(GH Archive) 표본으로 추정하고 `≈`를 붙여요. ±25% 정도 차이 날 수 있어요.
- 별 대비 포크가 아주 적으면 순위에는 두되 "가짜 스타 의심" 경고를 달아요.

**⑤ 지난주와 비교**

- 지난주 리포트와 비교해서 `새로 진입`, `지난주 3위 ▲2`처럼 표시해요.
- 지난주 10위 안에 있다가 빠진 저장소는 "빠진 곳"에 보여 줘요.

**⑥ 한국어 요약**

"한 줄 / 단, 확인할 것 / 설치 한 줄"을 써요. `config.toml`의 `[summary].mode`로 정해요.
- `claude-task` (기본): API 키 없이 Claude 예약 작업이 매주 채워요. 절차는 [docs/claude-weekly-task.md](docs/claude-weekly-task.md).
- `api`: `ANTHROPIC_API_KEY` Secret으로 리포트를 만들 때 바로 요약해요.
- `off`: 저장소 설명만 써요.

## 설치

1. **Settings → Secrets and variables → Actions**에 필요한 것만 넣어요.

   | 이름 | 필수 | 용도 |
   |---|---|---|
   | `SLACK_WEBHOOK_URL` | 선택 | Slack Incoming Webhook ([만들기](https://api.slack.com/messaging/webhooks)) |
   | `DISCORD_WEBHOOK_URL` | 선택 | Discord 채널 웹훅 |
   | `GENERIC_WEBHOOK_URL` | 선택 | 결과 JSON을 받을 주소 (n8n, Zapier, 사내 봇 등) |
   | `ANTHROPIC_API_KEY` | 선택 | `summary.mode = "api"`일 때만 |
   | `GH_PAT` | 권장 | **classic** 개인 토큰, 권한(scope) 체크 없이. 기본 Actions 토큰과 fine-grained 토큰은 별 누른 기록을 못 읽어서, 이게 없으면 첫 주와 지난 주 채우기(`--as-of`)는 새로 생긴 저장소만 집계돼요 |

   소스마다 다른 채널로 보내려면 이름 뒤에 `_<소스 대문자>`를 붙여요. 예: `SLACK_WEBHOOK_URL_GITHUB_RISING`.
   (워크플로의 `env:`에도 같은 이름을 추가해 주세요.)
2. 웹페이지와 RSS: **Settings → Pages → Source: GitHub Actions**로 켜요. 주소는 `https://daewoong-axtf.github.io/ax-radar/`, 피드는 `.../github-rising/feed.xml`이에요.
3. **Actions → github-rising → Run workflow**로 한 번 돌려 봐요.

## 직접 실행

```bash
export GITHUB_TOKEN=ghp_...
python -m radar github_rising snapshot
python -m radar github_rising report --no-notify   # 알림 없이
python -m radar github_rising report --dry-run     # 저장도 안 하고 화면에만
python -m radar github_rising pending              # 요약이 빈 항목 (JSON)
python -m radar github_rising enrich --file s.json # 요약 합치기
python -m radar github_rising publish              # 페이지 다시 만들고 안 보낸 알림 보내기
python -m radar github_rising site                 # 페이지만 다시 만들기 (public/)
python -m unittest discover tests
```

Python 3.11 이상, 표준 라이브러리만 써요 (요약을 쓸 때만 `pip install anthropic`).

## 새 소스 붙이기

1. `radar/sources/<이름>/__init__.py`에 `COMMANDS = ("run",)`와 `run(command, cfg, gh, args, log)`를 만들어요.
2. `run()`은 알림이 필요하면 `{"payloads": {"slack": {...}, "discord": {...}, "generic_webhook": {...}}}`를 돌려줘요.
3. `radar/__main__.py`의 `SOURCES`에 등록하고, `config.toml`에 `[<이름>]` 섹션, `.github/workflows/`에 스케줄을 추가해요.

## 알아 둘 것

- **첫 주 정확도**: GitHub stargazers API는 앞에서 4만 개까지만 보여 줘서, 별이 4만 개 넘는 대형 저장소는 첫 주에 빠져요. 매일 스냅샷이 쌓이는 둘째 주부터 모두 정확해요.
- **가짜 스타**: 신규 저장소 상위권에 별을 사서 올린 저장소가 섞여요. 포크 수 필터와 경고로 줄이지만 완벽하진 않아서, `[github_rising.filter].exclude`로 직접 빼 주세요.
- 이 순위는 GitHub 별 급상승 순위예요. 후보는 GitHub Trending과 검색으로 모으고, 순위는 7일 동안 늘어난 별 수를 직접 세서 매겨요. 그래서 GitHub 공식 Trending 순서와는 다를 수 있어요.
