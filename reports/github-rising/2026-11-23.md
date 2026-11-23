# 11월 넷째 주 GitHub 별 급상승 AI·개발 도구 BEST 6

TOP 시리즈 · 2026-11-23

> 집계 기간: 2026-11-16 13:28 ~ 2026-11-23 13:28 (KST). GitHub API로 별 수를 직접 세서 만든 순위예요. GitHub 공식 트렌딩 순위가 아니에요.
> 첫 주라 7일 전 기록이 없고 별 기록도 읽지 못해서, 이번 주에 새로 생긴 저장소만 집계했어요. 다음 주부터는 매일 기록과 비교해서 전체 후보를 집계해요.

| 순위 | 저장소 | 별 증가 | 지난주 대비 | 라이선스 | 한 줄 | 단, 확인할 것 |
|---|---|---|---|---|---|---|
| 1 | [erkamyaman/rust-anything](https://github.com/erkamyaman/rust-anything) | +8,103 | - | MIT | 앱을 조각조각 Rust로 옮기고, 원본과 똑같이 동작하는지 기록으로 검증하는 도구 | Rust 코드는 내 코딩 에이전트(Claude Code 등)가 써요. PHP·C#은 함수 단위 포팅만 돼요 (README) |
| 2 | [bookwjitchieni1986/blender-ai-mcp-addon](https://github.com/bookwjitchieni1986/blender-ai-mcp-addon) | +2,753 | - | MIT | 블렌더 안에서 AI와 대화하며 장면을 만드는 애드온 겸 MCP 서버 | Windows x64·Blender 4.2 이상 전용 ZIP 배포예요 (README). 계정 이름이 무작위이고 설명이 키워드 나열이라, 설치 전에 릴리스 파일과 코드를 꼭 확인하세요 |
| 3 | [iamajmeena/neonclipping](https://github.com/iamajmeena/neonclipping) | +2,122 | - | MIT | 긴 영상 링크를 넣으면 자막 달린 세로 쇼츠 클립을 만들어 주는 로컬 도구 | Python 3.10~3.13과 FFmpeg가 필요하고, 하이라이트 고르기에 로컬 LLM(Ollama)을 써요 (README) |
| 4 | [EL4CTEO/fast-anything](https://github.com/EL4CTEO/fast-anything) | +2,095 | - | MIT | 느린 함수 5%만 찾아 Rust로 바꾸고 결과가 같은지 검증하는 성능 도구 | Rust 툴체인(rustup)이 필요하고, 포팅은 코딩 에이전트에게 맡기는 방식이에요 (README) |
| 5 | [sybil-solutions/inference-optimisation-skill](https://github.com/sybil-solutions/inference-optimisation-skill) | +1,974 | - | MIT | 로컬 LLM 서버 속도를 단계별로 끌어올리는 에이전트 스킬(작업 지침서) | 실행 프로그램이 아니라 SKILL.md 지침이에요. 직접 GPU 서버를 돌리는 사람에게만 쓸모 있어요 (README) |
| 6 | [INK-Q/agy-fast](https://github.com/INK-Q/agy-fast) | +592 | - | MIT | 구글 Antigravity 에이전트의 대기 시간과 토큰 사용량을 줄이는 MCP 플러그인 | Google Antigravity 전용이고 Node.js 20 이상이 필요해요. 설치는 원격 스크립트를 바로 실행하는 방식이라 내용을 먼저 보세요 (README) |

## 바로 써 보기 (설치 한 줄)

**1위 erkamyaman/rust-anything**

```bash
cargo install rust-anything
```

**4위 EL4CTEO/fast-anything**

```bash
npm i -g @el4cteo/fast-anything
```

**5위 sybil-solutions/inference-optimisation-skill**

```bash
git clone https://github.com/sybil-solutions/inference-optimisation-skill
```

**6위 INK-Q/agy-fast**

```bash
curl -fsSL https://raw.githubusercontent.com/INK-Q/agy-fast/main/install.sh | sh
```


## 출처

- GitHub REST API: 검색(`/search/repositories`), 저장소 정보(`/repos`), 별 기록(`/repos/{owner}/{repo}/stargazers`)
- 후보 6개 중 별 증가 순. 필터: 포크 5개 이상, AI 관련 키워드
