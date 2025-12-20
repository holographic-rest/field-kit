import express from 'express';
import { fileURLToPath } from 'url';
import path from 'path';
import fs from 'fs';
import dotenv from 'dotenv';
import OpenAI from 'openai';

// ESM-friendly __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Environment loading order:
// 1. If OPENAI_API_KEY already set, use it
// 2. Else try repo-root .env (two levels up from server/)
// 3. Else try wrapper/.env if it exists
if (!process.env.OPENAI_API_KEY) {
  const repoRootEnvPath = path.resolve(__dirname, '../../.env');
  const wrapperEnvPath = path.resolve(__dirname, '../.env');

  if (fs.existsSync(repoRootEnvPath)) {
    dotenv.config({ path: repoRootEnvPath });
    console.log('Loaded env from repo root .env');
  } else if (fs.existsSync(wrapperEnvPath)) {
    dotenv.config({ path: wrapperEnvPath });
    console.log('Loaded env from wrapper/.env');
  }
}

const PORT = process.env.PORT || 3001;

// Validate API key
if (!process.env.OPENAI_API_KEY) {
  console.error('ERROR: OPENAI_API_KEY not found.');
  console.error('Set it in environment or create a .env file at repo root.');
  process.exit(1);
}

// Initialize OpenAI client
const client = new OpenAI({
  apiKey: process.env.OPENAI_API_KEY,
});

// Initialize Express
const app = express();
app.use(express.json());

// Serve static files from client/
const clientPath = path.resolve(__dirname, '../client');
app.use(express.static(clientPath));

// Health check
app.get('/api/health', (req, res) => {
  res.json({ ok: true });
});

// Chat endpoint (non-streaming, for backwards compat)
app.post('/api/chat', async (req, res) => {
  const { messages } = req.body;

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: 'messages array is required' });
  }

  for (const msg of messages) {
    if (!msg.role || !msg.content) {
      return res.status(400).json({ error: 'Each message must have role and content' });
    }
  }

  try {
    const response = await client.responses.create({
      model: 'gpt-5.2',
      input: messages,
    });

    res.json({ reply: response.output_text });
  } catch (error) {
    console.error('OpenAI API error:', error.message);
    res.status(500).json({ error: error.message || 'Failed to get response from OpenAI' });
  }
});

// Streaming chat endpoint
app.post('/api/chat/stream', async (req, res) => {
  const { messages } = req.body;

  if (!messages || !Array.isArray(messages) || messages.length === 0) {
    return res.status(400).json({ error: 'messages array is required' });
  }

  for (const msg of messages) {
    if (!msg.role || !msg.content) {
      return res.status(400).json({ error: 'Each message must have role and content' });
    }
  }

  // Set headers for streaming
  res.setHeader('Content-Type', 'application/x-ndjson');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');

  try {
    const stream = await client.responses.create({
      model: 'gpt-5.2',
      input: messages,
      stream: true,
    });

    for await (const event of stream) {
      // Handle different event types from the Responses API
      if (event.type === 'response.output_text.delta') {
        res.write(JSON.stringify({ type: 'delta', text: event.delta }) + '\n');
      } else if (event.type === 'response.completed') {
        res.write(JSON.stringify({ type: 'done' }) + '\n');
      }
    }

    res.end();
  } catch (error) {
    console.error('OpenAI streaming error:', error.message);

    // If headers already sent, send error as NDJSON
    if (res.headersSent) {
      res.write(JSON.stringify({ type: 'error', message: error.message }) + '\n');
      res.end();
    } else {
      res.status(500).json({ error: error.message || 'Failed to stream response' });
    }
  }
});

// Start server with error handling
const server = app.listen(PORT, () => {
  console.log(`Server running at http://localhost:${PORT}`);
});

server.on('error', (err) => {
  if (err.code === 'EADDRINUSE') {
    console.error(`\nPort ${PORT} is already in use.`);
    console.error(`\nTo fix this, run:\n  lsof -ti:${PORT} | xargs kill -9\n`);
    console.error(`Or use a different port:\n  PORT=3002 npm run dev\n`);
  } else {
    console.error('Server error:', err.message);
  }
  process.exit(1);
});
