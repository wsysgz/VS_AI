# LiteLLM Gateway First Rollout Design

> Workspace: `D:\GitHub\auto`
>
> Scope: add an explicit, optional LiteLLM gateway path without removing the current direct DeepSeek / MiniMax paths.

## Goal

Make LiteLLM Gateway a first-class provider contract in the repo while keeping direct provider mode as the default rollback path.

## Design summary

- Add a named provider contract: `AI_PROVIDER=litellm_proxy`
- Use LiteLLM alias models such as `vs-ai-analysis` and `vs-ai-summary`
- Keep the repo HTTP client unchanged apart from provider defaults and auth resolution
- Ship a local gateway config example under `config/litellm/`
- Update docs so the rollout is stage-scoped: P2-B only

## Phase boundary

This rollout includes:

1. provider defaults
2. settings exposure
3. sample gateway config
4. docs and handoff guidance
5. targeted tests

This rollout does not include:

- Langfuse tracing
- Feishu card redesign
- Feishu bitable ops surface
- mandatory gateway cutover for every environment

## Feishu phase placement

- `P3-A`: Feishu push interface optimization via static cards + text fallback
- `P3-B`: Feishu bitable operations surface for governance / approvals / dashboards

## Success criteria

1. `litellm_proxy` resolves with a usable default base URL and key env
2. stage-specific LiteLLM aliases can be selected via existing stage envs
3. settings expose `LITELLM_MASTER_KEY`
4. repo docs explain the optional gateway path and rollback path
5. tests prove the new provider contract works
