// DOM elements
const messagesEl = document.getElementById('messages');
const landingEl = document.getElementById('landing');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const stopBtn = document.getElementById('stopBtn');
const newChatBtn = document.getElementById('newChatBtn');
const jumpToLatestBtn = document.getElementById('jumpToLatest');
const sidebar = document.getElementById('sidebar');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebarOpen = document.getElementById('sidebarOpen');
const conversationList = document.getElementById('conversationList');
const promptChips = document.getElementById('promptChips');

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
});

// State
let conversations = [];
let currentConversationId = null;
let currentMessages = [];
let isStreaming = false;
let abortController = null;
let userScrolledUp = false;

// Initialize
init();

function init() {
  loadConversations();
  setupEventListeners();

  if (conversations.length === 0) {
    createNewConversation();
  } else {
    loadConversation(conversations[0].id);
  }

  updateUI();
  inputEl.focus();
}

// Local storage
function loadConversations() {
  try {
    const stored = localStorage.getItem('gpt-conversations');
    if (stored) {
      conversations = JSON.parse(stored);
    }
  } catch (e) {
    console.error('Failed to load conversations:', e);
    conversations = [];
  }
}

function saveConversations() {
  try {
    localStorage.setItem('gpt-conversations', JSON.stringify(conversations));
  } catch (e) {
    console.error('Failed to save conversations:', e);
  }
}

function createNewConversation() {
  const conv = {
    id: Date.now().toString(),
    title: 'New chat',
    createdAt: new Date().toISOString(),
    messages: [],
  };
  conversations.unshift(conv);
  saveConversations();
  loadConversation(conv.id);
}

function loadConversation(id) {
  const conv = conversations.find(c => c.id === id);
  if (!conv) return;

  currentConversationId = id;
  currentMessages = conv.messages;
  updateUI();
  renderMessages();
  renderConversationList();
}

function updateCurrentConversation() {
  const conv = conversations.find(c => c.id === currentConversationId);
  if (conv) {
    conv.messages = currentMessages;

    // Update title from first user message
    const firstUserMsg = currentMessages.find(m => m.role === 'user');
    if (firstUserMsg) {
      conv.title = firstUserMsg.content.slice(0, 40) + (firstUserMsg.content.length > 40 ? '...' : '');
    }

    saveConversations();
    renderConversationList();
  }
}

function deleteConversation(id) {
  conversations = conversations.filter(c => c.id !== id);
  saveConversations();

  if (id === currentConversationId) {
    if (conversations.length > 0) {
      loadConversation(conversations[0].id);
    } else {
      createNewConversation();
    }
  } else {
    renderConversationList();
  }
}

// Event listeners
function setupEventListeners() {
  // Input handling
  inputEl.addEventListener('input', () => {
    autoResizeTextarea();
    sendBtn.disabled = !inputEl.value.trim() || isStreaming;
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  sendBtn.addEventListener('click', sendMessage);
  stopBtn.addEventListener('click', stopStreaming);
  newChatBtn.addEventListener('click', createNewConversation);

  // Jump to latest
  jumpToLatestBtn.addEventListener('click', () => {
    scrollToBottom();
    userScrolledUp = false;
    jumpToLatestBtn.classList.remove('visible');
  });

  // Scroll detection
  messagesEl.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = messagesEl;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

    if (isNearBottom) {
      userScrolledUp = false;
      jumpToLatestBtn.classList.remove('visible');
    } else if (!isStreaming) {
      userScrolledUp = true;
      jumpToLatestBtn.classList.add('visible');
    }
  });

  // Sidebar
  sidebarOpen.addEventListener('click', () => sidebar.classList.add('open'));
  sidebarToggle.addEventListener('click', () => sidebar.classList.remove('open'));

  // Prompt chips
  promptChips.querySelectorAll('.chip').forEach(chip => {
    chip.addEventListener('click', () => {
      inputEl.value = chip.textContent;
      autoResizeTextarea();
      sendBtn.disabled = false;
      inputEl.focus();
    });
  });
}

function autoResizeTextarea() {
  inputEl.style.height = 'auto';
  inputEl.style.height = Math.min(inputEl.scrollHeight, 200) + 'px';
}

// UI updates
function updateUI() {
  const hasMessages = currentMessages.length > 0;

  if (hasMessages) {
    landingEl.classList.add('hidden');
    messagesEl.classList.add('visible');
  } else {
    landingEl.classList.remove('hidden');
    messagesEl.classList.remove('visible');
  }
}

function renderMessages() {
  messagesEl.innerHTML = currentMessages.map((msg, i) => renderMessage(msg, i)).join('');
  addCopyButtonListeners();

  if (!userScrolledUp) {
    scrollToBottom();
  }
}

function renderMessage(msg, index) {
  const isUser = msg.role === 'user';
  const isError = msg.error;
  const cls = isUser ? 'user' : isError ? 'error' : 'assistant';

  let content;
  if (isUser) {
    content = escapeHtml(msg.content);
  } else if (isError) {
    content = escapeHtml(msg.content);
  } else {
    content = renderMarkdown(msg.content);
  }

  return `
    <div class="message ${cls}" data-index="${index}">
      <div class="message-content">${content}</div>
    </div>
  `;
}

function renderMarkdown(text) {
  if (!text) return '';

  // Parse markdown
  let html = marked.parse(text);

  // Wrap code blocks with copy button
  html = html.replace(/<pre><code([^>]*)>([\s\S]*?)<\/code><\/pre>/g, (match, attrs, code) => {
    return `<div class="code-block-wrapper"><button class="copy-btn">Copy</button><pre><code${attrs}>${code}</code></pre></div>`;
  });

  return html;
}

function addCopyButtonListeners() {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const codeBlock = btn.nextElementSibling.querySelector('code');
      const text = codeBlock.textContent;

      try {
        await navigator.clipboard.writeText(text);
        btn.textContent = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {
          btn.textContent = 'Copy';
          btn.classList.remove('copied');
        }, 2000);
      } catch (e) {
        console.error('Copy failed:', e);
      }
    });
  });
}

function renderConversationList() {
  conversationList.innerHTML = conversations.map(conv => `
    <div class="conversation-item ${conv.id === currentConversationId ? 'active' : ''}" data-id="${conv.id}">
      ${escapeHtml(conv.title)}
    </div>
  `).join('');

  conversationList.querySelectorAll('.conversation-item').forEach(item => {
    item.addEventListener('click', () => {
      loadConversation(item.dataset.id);
      sidebar.classList.remove('open');
    });
  });
}

function scrollToBottom() {
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

// Send message with streaming
async function sendMessage() {
  const content = inputEl.value.trim();
  if (!content || isStreaming) return;

  // Add user message
  currentMessages.push({ role: 'user', content });
  updateCurrentConversation();
  updateUI();
  renderMessages();

  // Clear input
  inputEl.value = '';
  inputEl.style.height = 'auto';
  sendBtn.disabled = true;

  // Start streaming
  isStreaming = true;
  abortController = new AbortController();
  sendBtn.style.display = 'none';
  stopBtn.style.display = 'block';

  // Add empty assistant message with typing indicator
  const assistantIndex = currentMessages.length;
  currentMessages.push({ role: 'assistant', content: '' });
  renderMessages();

  // Show typing indicator
  const lastMessage = messagesEl.querySelector(`[data-index="${assistantIndex}"] .message-content`);
  lastMessage.innerHTML = '<div class="typing-indicator"><span></span><span></span><span></span></div>';

  try {
    const response = await fetch('/api/chat/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: currentMessages.slice(0, -1) }),
      signal: abortController.signal,
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.error || 'Request failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.trim()) continue;

        try {
          const data = JSON.parse(line);

          if (data.type === 'delta') {
            fullText += data.text;
            currentMessages[assistantIndex].content = fullText;
            lastMessage.innerHTML = renderMarkdown(fullText);
            addCopyButtonListeners();

            if (!userScrolledUp) {
              scrollToBottom();
            }
          } else if (data.type === 'error') {
            throw new Error(data.message);
          }
        } catch (e) {
          if (e.message !== 'Unexpected end of JSON input') {
            console.error('Parse error:', e);
          }
        }
      }
    }

    // Finalize
    currentMessages[assistantIndex].content = fullText;
    updateCurrentConversation();
    renderMessages();

  } catch (error) {
    if (error.name === 'AbortError') {
      // User stopped
      if (!currentMessages[assistantIndex].content) {
        currentMessages.pop();
      }
    } else {
      currentMessages[assistantIndex] = {
        role: 'assistant',
        content: error.message || 'Something went wrong',
        error: true,
      };
    }

    updateCurrentConversation();
    renderMessages();
  }

  isStreaming = false;
  abortController = null;
  sendBtn.style.display = 'flex';
  stopBtn.style.display = 'none';
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
}

function stopStreaming() {
  if (abortController) {
    abortController.abort();
  }
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
