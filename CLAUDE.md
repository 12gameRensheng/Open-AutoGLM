# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Phone Agent is an AI-powered Android phone automation framework built on AutoGLM. It uses vision-language models to understand phone screens and execute tasks via ADB (Android Debug Bridge). Users describe tasks in natural language (e.g., "Open Xiaohongshu and search for food") and the agent autonomously parses intent, understands the interface, and executes actions.

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt
pip install -e .

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run the agent (interactive mode)
python main.py --base-url http://localhost:8000/v1 --model "autoglm-phone-9b"

# Run single task
python main.py --base-url http://localhost:8000/v1 "Open Chrome browser"

# List supported apps
python main.py --list-apps

# List connected devices
python main.py --list-devices
```

### Pre-commit Hooks

The project uses ruff for linting/formatting, typos for spell checking, and pymarkdown for markdown linting. These run automatically on commit.

## Architecture

```
User Task (natural language)
    ↓
PhoneAgent.run() ──────────────────────────────────┐
    │                                               │
    ├─→ get_screenshot() → base64 image            │
    ├─→ get_current_app() → app package name       │
    │                                               │
    ├─→ MessageBuilder.create_user_message()       │ Loop until
    │   (text + screenshot)                        │ finish or
    │                                               │ max_steps
    ├─→ ModelClient.request() → thinking + action  │
    │                                               │
    └─→ ActionHandler.execute() → device control ──┘
```

### Key Components

- **PhoneAgent** (`phone_agent/agent.py`): Main orchestrator. Manages the automation loop with `run()` for full execution or `step()` for debugging. Uses `AgentConfig` for settings and `StepResult` for step outcomes.

- **ModelClient** (`phone_agent/model/client.py`): OpenAI-compatible client for vision-language model. Uses `MessageBuilder` helper to construct multimodal messages (text + base64 images).

- **ActionHandler** (`phone_agent/actions/handler.py`): Parses model output and executes actions. Converts relative coordinates (0-1000) to absolute pixels. Supports callbacks for sensitive operations and manual takeover.

- **ADB Module** (`phone_agent/adb/`):
  - `connection.py`: USB/WiFi device connection management
  - `screenshot.py`: Screen capture to base64
  - `device.py`: Tap, swipe, back, home, launch_app
  - `input.py`: Text input via ADB Keyboard

- **Config** (`phone_agent/config/`):
  - `apps.py`: Package name mappings for 50+ Chinese apps
  - `prompts_zh.py` / `prompts_en.py`: System prompts by language
  - `i18n.py`: UI message strings

### Action Types

Actions use relative coordinates (0-1000 range). The handler supports: Launch, Tap, Double Tap, Long Press, Swipe, Type, Type_Name, Back, Home, Wait, Interact, Note, Call_API, Take_over, Finish.

### Callback System

Two callback hooks for human-in-the-loop scenarios:
- `confirmation_callback(message) -> bool`: For sensitive operations (payment, auth)
- `takeover_callback(message) -> None`: For manual intervention (captcha, login)

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PHONE_AGENT_BASE_URL` | Model API URL | `http://localhost:8000/v1` |
| `PHONE_AGENT_MODEL` | Model name | `autoglm-phone-9b` |
| `PHONE_AGENT_MAX_STEPS` | Max iterations per task | `100` |
| `PHONE_AGENT_DEVICE_ID` | ADB device ID | (auto-detect) |
| `PHONE_AGENT_LANG` | Language: `cn` or `en` | `cn` |

## Model Deployment

Deploy AutoGLM-Phone-9B via vLLM with these required parameters:

```bash
python3 -m vllm.entrypoints.openai.api_server \
  --served-model-name autoglm-phone-9b \
  --allowed-local-media-path / \
  --mm-encoder-tp-mode data \
  --mm_processor_cache_type shm \
  --mm_processor_kwargs '{"max_pixels":5000000}' \
  --max-model-len 25480 \
  --chat-template-content-format string \
  --limit-mm-per-prompt '{"image":10}' \
  --model zai-org/AutoGLM-Phone-9B \
  --port 8000
```

## Windows Notes

For encoding issues (`UnicodeEncodeError gbk`), prefix commands with: `PYTHONIOENCODING=utf-8`
