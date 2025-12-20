# GPT-5.2 Chat Wrapper

Minimal ChatGPT-like interface for GPT-5.2 with streaming, markdown rendering, and local conversation persistence.

## Features

- Dark ChatGPT-like UI
- Streaming responses with live text rendering
- Markdown + code blocks with copy button
- Local conversation history (localStorage)
- Stop button to cancel generation
- Landing state with prompt chips
- Auto-scroll with "Jump to latest" button

## Run

### Option A: From repo root (recommended)

```bash
npm --prefix wrapper install
npm --prefix wrapper run dev
```

Open http://localhost:3001

### Option B: From wrapper folder

```bash
cd wrapper
npm install
npm run dev
```

Open http://localhost:3001

## Environment

The server loads `OPENAI_API_KEY` in this order:

1. Already set in environment
2. Repo-root `.env` file
3. `wrapper/.env` (if exists)

## Test endpoints

Health check:

```bash
curl -s http://localhost:3001/api/health
```

Chat (non-streaming):

```bash
curl -s http://localhost:3001/api/chat \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Say hello"}]}'
```

Chat (streaming):

```bash
curl -s http://localhost:3001/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Count to 5"}]}'
```

## Keyboard shortcuts

- **Enter**: Send message
- **Shift+Enter**: New line

## Experiment note

This is a standalone experiment. Do not push until verified working.
