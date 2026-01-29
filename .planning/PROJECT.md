# Agno + Keycycle Integration

## What This Is

Integration of Agno (multi-agent framework) and Keycycle (API key rotation) into HFS to replace MockLLMClient with real LLM-powered triad execution. Triads become Agno Teams, with intelligent model selection based on role and adaptive escalation on failure.

## Core Value

Real LLM-powered multi-agent negotiation with automatic key rotation and failure-adaptive model escalation.

## Requirements

### Validated

- ✓ HFS 9-phase pipeline — existing
- ✓ Triad presets (Hierarchical, Dialectic, Consensus) — existing
- ✓ Spec negotiation mechanics — existing
- ✓ Configuration system (YAML + Pydantic) — existing
- ✓ CLI interface — existing

### Active

- [ ] Replace MockLLMClient with Agno-backed real LLM calls
- [ ] Triads implemented as Agno Teams with 3 agent members
- [ ] Keycycle integration for automatic key rotation across providers
- [ ] Multi-provider support: Cerebras (51 keys), Groq (16), Gemini (110), OpenRouter (31)
- [ ] Configurable model tiers in YAML (role-based defaults)
- [ ] Adaptive model escalation when execution fails
- [ ] Code execution uses high-quality models (GLM-4.7, OSS-120b via Cerebras)
- [ ] OpenTelemetry tracing to TiDB for observability
- [ ] Usage statistics persisted to TiDB via Keycycle
- [ ] Remove MockLLMClient entirely (no fallback)

### Out of Scope

- Learning mode (agents improving over time) — complexity, defer to future
- Human-in-the-loop approval for tool execution — not needed for v1
- Session persistence across runs — each run is independent
- Mobile/web UI — CLI-only for now

## Context

**Existing Codebase:**
- HFS is a working multi-agent negotiation pipeline with 9 phases
- Currently uses MockLLMClient that returns placeholder responses
- Triads have deliberate/negotiate/execute methods that call `llm_client.messages_create()`
- Agno is already in `.venv` (installed as dependency)
- Keycycle provides `MultiProviderWrapper.get_model()` returning rotating Agno models

**API Keys Available (.env):**
- Cerebras: 51 keys (includes code models GLM-4.7, OSS-120b)
- Groq: 16 keys (Llama-based, fast inference)
- Gemini: 110 keys (Google models)
- OpenRouter: 31 keys (multi-model access)
- Database: TiDB (TIDB_DB_URL for usage persistence)

**Integration Docs:**
- `docs/AGNO.md` — Full integration guide with code examples
- `docs/KEYCYCLE.md` — Key rotation and Agno model integration

## Constraints

- **Providers**: Must use Keycycle's numbered env var format (already matches .env)
- **Code Quality**: Code execution phase always uses GLM-4.7 or OSS-120b (Cerebras)
- **Architecture**: Triads must become Agno Teams (not standalone agents)
- **Persistence**: Usage stats go to TiDB (TIDB_DB_URL already configured)
- **No Mocks**: Remove MockLLMClient entirely — require real API keys to run

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Agno Teams for triads | Built-in coordination, history management | — Pending |
| Role-based + pressure-linked model tiers | Start cheap, escalate on failure | — Pending |
| Cerebras for code models | GLM-4.7/OSS-120b quality, 51 keys available | — Pending |
| TiDB for usage persistence | Already have TIDB_DB_URL, production-grade | — Pending |
| Remove MockLLMClient | Clean slate, force real integration | — Pending |

---
*Last updated: 2026-01-29 after initialization*
