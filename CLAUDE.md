# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Supply Chain API built with FastAPI + SQLAlchemy + AgentScope. The project integrates AI agents for intelligent logistics tracking and address matching using DashScope (Qwen) models.

## Running the Application

```bash
# Install dependencies
pip install -r requirements.txt

# Copy environment variables
cp .env.example .env
# Edit .env and set DASHSCOPE_API_KEY

# Run development server
uvicorn app.main:app --reload

# Or with specific host/port
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# API docs available at:
# http://localhost:8000/docs (Swagger UI)
# http://localhost:8000/redoc (ReDoc)
```

## Required Environment Variables

In `.env`, set:
- `DASHSCOPE_API_KEY` - Required for AgentScope agents and address matching
- `DATABASE_URL` - Database connection (default: SQLite)

## Architecture

### Layered Architecture

```
routers/     → HTTP request/response handling, parameter validation
services/    → Business logic, agent orchestration
models/      → SQLAlchemy ORM models
schemas/     → Pydantic models for request/response validation
core/        → Configuration, database connections
agents/      → AgentScope AI agents
```

### Multi-Agent System (Logistics)

The logistics tracking system uses a 4-agent architecture coordinated via `LogisticsService`:

1. **Perceiver** (`logistics_perception_agent.py`) - Extracts logistics numbers, addresses, entities from user input/images
2. **Reasoner** (`logistics_reasoning_agent.py`) - Analyzes user intent (query/modify/insert), plans execution steps
3. **Actor** (`logistics_action_agent.py`) - Executes business operations (pseudo-code APIs to be implemented)
4. **Dialog** (`logistics_dialog_agent.py`) - Generates user-friendly responses

### Session Management

- `SessionManager` uses `AsyncSQLAlchemyMemory` for persistent conversation context
- Stores dialogue history in SQLite: `supply_chain_memory.db`
- Supports multi-turn conversations with context retention

### MCP Tools Integration

- `app/tools/tool_registry.py` registers MCP (Model Context Protocol) tools
- `app/tools/mcp_clients.py` contains MCP client implementations
- Currently integrated: Gaode Map (Amap) tools for address services
- Initialize tools via `initialize_tools()` in lifespan

### AgentScope Initialization

The application initializes AgentScope in `main.py` lifespan:
```python
agentscope.init()  # Initialize AgentScope framework
await initialize_tools()  # Register MCP tools
```

## Adding New Features

### New API Endpoint

1. Create Schema in `schemas/` (Pydantic models)
2. Create Service in `services/` (business logic)
3. Create Router in `routers/` (HTTP endpoints)
4. Register router in `main.py`: `app.include_router(module.router, prefix="/api/v1")`

### New Agent

1. Extend `ReActAgent` or `AgentBase`
2. Define structured output model using `pydantic.BaseModel`
3. Implement agent methods with proper sys_prompt
4. Initialize in `LogisticsService.initialize()` for logistics agents

## Key Patterns

### Router Layer
- Use `APIRouter(prefix="...", tags=["..."])`
- Pydantic schemas for request/response models
- Convert Pydantic models to dicts before passing to services: `[item.model_dump() for item in request.content]`
- Call services, handle exceptions, return HTTP responses

### Service Layer
- Business logic and data processing
- For agents: coordinate multi-agent workflows using sequential calls
- Return `{"success": bool, "message": str, "data": dict}` format

### Database
- SQLAlchemy ORM with async support via `aiosqlite`
- Models extend `BaseModel` from `app.models.base`
- Use `get_db()` dependency injection in routers

### Address Matching
- Uses `AddressService.match_addresses()` with ReActAgent
- MCP Gaode Map tools registered in `tool_registry.py`
- Expects `AddressMatchRequest` with source/candidates

## Important Files

| File | Purpose |
|------|---------|
| `app/main.py` | Application entry, lifespan management, router registration |
| `app/core/config.py` | Settings via Pydantic BaseSettings |
| `app/core/database.py` | Database engine and session management |
| `app/services/logistics_service.py` | Multi-agent orchestration for logistics |
| `app/services/session_manager.py` | Conversation context persistence |
| `app/services/address_service.py` | Address matching with agents |
| `app/tools/tool_registry.py` | MCP tool registration |
