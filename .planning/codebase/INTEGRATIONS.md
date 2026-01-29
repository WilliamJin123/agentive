# External Integrations

**Analysis Date:** 2026-01-29

## APIs & External Services

**LLM Provider (Required):**
- Anthropic Claude API - AI agent reasoning and code generation
  - SDK/Client: `anthropic>=0.18.0`
  - Auth: Configured via `llm_client` parameter to HFSOrchestrator
  - Usage: All triads call `llm_client.messages_create()` for agent deliberation
  - Interface: Async-compatible client with messages API
  - Entry point: `hfs/core/orchestrator.py` passes llm_client to all components
  - Model specified in config: `arbiter.model` (default: "claude-sonnet-4-20250514")

**Multi-Provider Support (Infrastructure for future):**
- `.env` file contains credentials for multiple LLM providers:
  - Cerebras API (51 keys configured)
  - Groq API (16 keys configured)
  - Google Gemini API (44+ keys configured)
  - OpenRouter API (31 keys configured)
  - Cohere API
  - Mistral API
  - DeepSeek API
  - EXA API (search/knowledge)
- Currently unused by HFS core (reserved for future multi-provider orchestration)

## Data Storage

**Databases:**
- None required - HFS is stateless
- Configuration: YAML files only (no persistent storage)
- All state exists in-memory during pipeline execution

**File Storage:**
- Local filesystem only
  - Output directory specified via CLI: `--output-dir` parameter
  - Artifacts saved as files: `output_dir / file_path`
  - No cloud storage integrations
  - No database backends

**Caching:**
- None - Each run is independent

## Authentication & Identity

**Auth Provider:**
- Custom API key management
  - Implementation: Environment variables and config file
  - Keys location: `.env` file in project root
  - Loaded by: Client applications (not HFS core)
  - HFS accepts pre-authenticated `llm_client` parameter

**LLM Client Requirements:**
- Must implement async interface:
  ```python
  async def messages_create(
      model: str,
      max_tokens: int,
      messages: list,
      **kwargs
  ) -> Dict[str, Any]
  ```
- Return format: `{"content": [{"type": "text", "text": "..."}], "model": "...", "stop_reason": "..."}`
- No built-in OAuth or identity management

## Monitoring & Observability

**Error Tracking:**
- Not integrated - Errors logged via Python logging
- Logging configuration: `hfs/cli/main.py` sets up `logging.basicConfig()`
- Log level: INFO by default, DEBUG with `--verbose` flag

**Logs:**
- Console output via standard Python logging
- JSON export available: Results saved to `hfs_report.json` in output directory
- No external log aggregation

**Optional Integration (Infrastructure):**
- `.env` contains Langfuse credentials (observability platform):
  - `LANGFUSE_SECRET_KEY`, `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_BASE_URL`
  - Currently unused by HFS core
  - Reserved for future observability integration

## CI/CD & Deployment

**Hosting:**
- Local/self-hosted only
- No cloud platform integrations

**CI Pipeline:**
- pytest test runner configured in `pyproject.toml`
- No CI service configured (GitHub Actions, GitLab CI, etc.)

**Testing Infrastructure:**
- pytest 7.0+
- pytest-asyncio for async test support
- Run command: `pytest tests/` from hfs directory

## Environment Configuration

**Required env vars:**
- None - HFS is dependency-agnostic
- LLM client passed as parameter to HFSOrchestrator
- Config file path specified via CLI or parameter

**Optional env vars (for client applications):**
- `ANTHROPIC_API_KEY` - For Anthropic client
- Multi-provider keys in `.env` (for future support)
- Stored in: `.env` file in project root

**Secrets location:**
- `.env` file (plain text, not recommended for production)
- Load via: `python-dotenv` or equivalent (not in core dependencies)
- Future: Use secure secret management (AWS Secrets Manager, HashiCorp Vault, etc.)

## Configuration Files

**Primary:**
- `hfs/config/default.yaml` - Default HFS settings
  - Triads definition
  - Pressure mechanics (temperature, negotiation rounds)
  - Output format and style system
  - Arbiter settings

**Examples:**
- `hfs/config/examples/minimal.yaml` - Minimal configuration
- `hfs/config/examples/standard.yaml` - Standard recommended config

**Runtime Config Loading:**
- `hfs/core/config.py` - Pydantic-based config validation
- `load_config(path)` - Load and validate YAML config
- `load_config_dict(dict)` - Load from Python dict

## Webhooks & Callbacks

**Incoming:**
- None - HFS is request/response based

**Outgoing:**
- None - Results returned to caller, not pushed to external services
- Output artifacts written to local filesystem
- Optional JSON report generated in output directory

## Code Generation Target

**Output Frameworks (Configurable):**
- React (default)
- Vue
- Svelte
- HTML
- Vanilla JavaScript

**Style Systems (Configurable):**
- Tailwind CSS (default)
- CSS Modules
- Styled Components
- Vanilla CSS

**Output Format:**
- Generated code files written to output directory
- Structured artifact with metadata in `hfs_report.json`
- Validation results included in report

## Async/Concurrency

**Async Framework:**
- Python asyncio (built-in)
- All LLM calls are async: `await llm_client.messages_create(...)`
- Triad deliberations run concurrently via asyncio.gather()
- Used in: `hfs/core/orchestrator.py` phase execution

## Dependency Management

**Installation:**
- `pip install -e .` - Editable install with dependencies
- `pip install -e ".[dev]"` - With dev dependencies (pytest, pytest-asyncio)

**Package Publishing:**
- Not published to PyPI
- Entry point: `hfs = "cli.main:main"` for command-line tool

---

*Integration audit: 2026-01-29*
