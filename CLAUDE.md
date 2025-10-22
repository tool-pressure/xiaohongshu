# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Xiaohongshu (Little Red Book) AI Content Generation & Publishing System** - a FastAPI web application that uses LLM agents and MCP (Model Context Protocol) to automate content creation and publishing workflow.

**Core Flow**: User provides topic → AI researches via search tools → AI writes article → AI formats for Xiaohongshu → AI publishes directly to platform

## Critical Dependencies

### External MCP Service (REQUIRED)
**You MUST have the [xiaohongshu-mcp](https://github.com/xpzouying/xiaohongshu-mcp) service running before this app works:**
```bash
# This service must be running at http://localhost:18060/mcp
git clone https://github.com/xpzouying/xiaohongshu-mcp.git
cd xiaohongshu-mcp
# Follow that project's README to start the service
```

### Python Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Start the FastAPI application
python app.py
# Default: http://localhost:8080

# For development with auto-reload
uvicorn app:app --reload --host 0.0.0.0 --port 8080
```

## Architecture

### Multi-Agent Content Generation System

This is an **agentic AI system** that orchestrates multiple tools through MCP to complete a complex workflow:

1. **ContentGenerator** (`core/content_generator.py`): The orchestrator
   - Manages a 3-step research plan (info retrieval → article writing → format & publish)
   - Coordinates multiple MCP tool servers (Jina/Tavily search, XHS publishing)
   - Implements iterative tool calling with LLM decision-making loop (max 10 iterations)
   - **Key Pattern**: Uses `get_tool_call_response()` → execute tools → `get_final_response()` cycle
   - Automatically stops iteration when publish succeeds (checks for "success"/"成功" in tool results)

2. **LLMClient** (`core/xhs_llm_client.py`): OpenAI-compatible LLM interface
   - Two key methods: `get_tool_call_response()` and `get_final_response()`
   - `get_final_response()` adds a system prompt that guides LLM to either call more tools OR provide final summary
   - Converts MCP tools to OpenAI function calling format
   - Error handling returns mock ErrorResponse objects to avoid breaking the flow

3. **Server** (`core/xhs_llm_client.py`): MCP server connection manager
   - Handles two types: `stdio` (npx-based) and `streamable_http` (HTTP-based)
   - XHS server uses `streamable_http` type
   - Uses AsyncExitStack for proper async resource cleanup
   - Implements retry mechanism (2 retries, 1 second delay)

4. **Tool Execution Loop** (in `ContentGenerator.execute_step()`):
   ```
   Loop (max 10 iterations):
   1. LLM decides which tools to call (or provides final answer)
   2. Execute all tool_calls in parallel
   3. Append tool results to message history
   4. If publish_content succeeds → break immediately
   5. Call get_final_response() to decide: continue with more tools OR finish
   6. Repeat or exit
   ```

### Configuration Management

**ConfigManager** (`config/config_manager.py`):
- Generates 3 config files: `app_config.json`, `servers_config.json`, `.env`
- All configs are derived from user input via web UI
- **Important**: Uses absolute paths calculated from `config_manager.py` location
- Automatically updates MCP server config when app config changes

### MCP Server Configuration

Three MCP servers are integrated:
1. **jina-mcp-tools**: Web search (stdio, npx-based)
2. **tavily-remote**: Deep web search (stdio, npx-based, recommended - 1000 free searches/month)
3. **xhs**: Xiaohongshu publishing (streamable_http type, requires external service)

## Key Design Patterns

### 1. Dynamic Research Planning
`ContentGenerator.get_research_plan()` generates a 3-step plan dynamically based on user topic:
- Step 1: Information retrieval (search for latest info, 3-4 images)
- Step 2: Article writing (800-1200 words, youth-friendly language with emoji)
- Step 3: Format adaptation & publishing (Xiaohongshu format, JSON structure, direct publish)

Each step has dependencies and builds on previous results.

### 2. Context-Aware System Prompts
The `execute_step()` method builds rich system prompts including:
- Research topic and goals
- Xiaohongshu content requirements (attract attention, conversational tone)
- Previous step results (to avoid redundant work)
- Execution guidance (use existing info vs. call new tools)

### 3. Publish Success Detection
```python
if tool_name == "publish_content":
    result_str = str(tool_result).lower()
    if "success" in result_str or "成功" in result_str or "published" in result_str:
        publish_success = True
        # Stop iteration immediately
```

### 4. Error Resilience
- LLMClient returns mock ErrorResponse objects instead of raising exceptions
- Tool execution has retry mechanism
- Publish failures are captured with detailed error messages
- Final results include `publish_success` and `publish_error` fields

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Main web interface |
| GET | `/api/config` | Get configuration (sensitive data masked) |
| POST | `/api/config` | Save configuration |
| POST | `/api/test-login` | Test XHS MCP service connection |
| POST | `/api/validate-model` | Validate LLM model availability |
| POST | `/api/generate-and-publish` | Main endpoint: generate content & publish |

## Configuration Requirements

Required via web UI (stored in `config/app_config.json`):
- `llm_api_key`: OpenAI-compatible API key
- `openai_base_url`: LLM API base URL (e.g., `https://usw.sealos.io/v1`)
- `default_model`: Model name (recommended: `claude-sonnet-4-20250514`)
- `xhs_mcp_url`: Xiaohongshu MCP service URL (default: `http://localhost:18060/mcp`)

Optional:
- `jina_api_key`: For Jina search
- `tavily_api_key`: For Tavily search (recommended)

## Important Implementation Notes

### When Modifying Content Generation Logic:
1. **Do not remove the iterative tool calling loop** - it's essential for the agent to adapt
2. **Preserve the publish success detection** - prevents infinite retries
3. **Keep the context compression** - system prompts include previous results but truncated to 1000 chars
4. **Maintain step dependencies** - Step 3 depends on Step 1 and 2 results

### When Adding New MCP Tools:
1. Add server config to `ContentGenerator._initialize_servers()`
2. Update `config/config_manager.py` to include new API keys/URLs
3. Add to web UI configuration form (`templates/index.html`)
4. Tool name must match exactly between MCP server and LLM function call

### Testing the System:
```bash
# 1. Ensure XHS MCP service is running
curl http://localhost:18060/mcp/health

# 2. Start the app
python app.py

# 3. Configure via web UI at http://localhost:8080
# 4. Test with a topic like "Transformer架构详解"
```

## Common Issues

1. **"未找到工具" (Tool not found)**: MCP server not initialized or tool name mismatch
2. **发布失败 (Publish failed)**: XHS MCP service not running or login expired
3. **达到最大迭代次数**: LLM stuck in tool calling loop - check if publish success detection is working
4. **Empty images array**: Search tools didn't return valid HTTPS image URLs

## Project Philosophy

This is designed as a **learning case for agent architectures**, not production-ready. The codebase demonstrates:
- Configurable MCP tool orchestration
- Multi-tool task completion
- Agent context management and compression
- Multi-turn dialogue and memory (through message history)

Future architecture goals mentioned in README:
- More flexible MCP configuration
- Enhanced context retrieval and compression
- Improved multi-turn dialogue and memory systems
