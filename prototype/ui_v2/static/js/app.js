// DOM elements
const itemsFeed = document.getElementById('itemsFeed');
const landingEl = document.getElementById('landing');
const inputEl = document.getElementById('input');
const sendBtn = document.getElementById('sendBtn');
const newSessionBtn = document.getElementById('newSessionBtn');
const jumpToLatestBtn = document.getElementById('jumpToLatest');
const creditsValue = document.getElementById('creditsValue');
const ledgerBtn = document.getElementById('ledgerBtn');
const ledgerModal = document.getElementById('ledgerModal');
const ledgerClose = document.getElementById('ledgerClose');
const ledgerContent = document.getElementById('ledgerContent');
const promptChips = document.getElementById('promptChips');

// Configure marked for safe rendering
marked.setOptions({
  breaks: true,
  gfm: true,
});

// State
let items = [];
let currentSuggestions = null;
let currentSuggestionItemId = null;
let isProcessing = false;
let userScrolledUp = false;

// Initialize
init();

async function init() {
  setupEventListeners();
  await checkAndInit();
  await loadItems();
  updateUI();
  inputEl.focus();
}

async function checkAndInit() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();

    if (!data.initialized) {
      // Auto-initialize
      await fetch('/api/init', { method: 'POST' });
    }

    await updateCredits();
  } catch (e) {
    console.error('Init error:', e);
  }
}

async function loadItems() {
  try {
    const res = await fetch('/api/items');
    const data = await res.json();
    items = data.items || [];
  } catch (e) {
    console.error('Load items error:', e);
    items = [];
  }
}

async function updateCredits() {
  try {
    const res = await fetch('/api/credits');
    const data = await res.json();
    creditsValue.textContent = data.balance;
  } catch (e) {
    console.error('Credits error:', e);
  }
}

// Event listeners
function setupEventListeners() {
  inputEl.addEventListener('input', () => {
    autoResizeTextarea();
    sendBtn.disabled = !inputEl.value.trim() || isProcessing;
  });

  inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      createQueueItem();
    }
  });

  sendBtn.addEventListener('click', createQueueItem);
  newSessionBtn.addEventListener('click', () => location.reload());

  jumpToLatestBtn.addEventListener('click', () => {
    scrollToBottom();
    userScrolledUp = false;
    jumpToLatestBtn.classList.remove('visible');
  });

  itemsFeed.addEventListener('scroll', () => {
    const { scrollTop, scrollHeight, clientHeight } = itemsFeed;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

    if (isNearBottom) {
      userScrolledUp = false;
      jumpToLatestBtn.classList.remove('visible');
    } else if (!isProcessing) {
      userScrolledUp = true;
      jumpToLatestBtn.classList.add('visible');
    }
  });

  // Ledger modal
  ledgerBtn.addEventListener('click', openLedger);
  ledgerClose.addEventListener('click', closeLedger);
  ledgerModal.addEventListener('click', (e) => {
    if (e.target === ledgerModal) closeLedger();
  });

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
  const hasItems = items.length > 0;

  if (hasItems) {
    landingEl.classList.add('hidden');
    itemsFeed.classList.add('visible');
  } else {
    landingEl.classList.remove('hidden');
    itemsFeed.classList.remove('visible');
  }

  renderItems();
}

function renderItems() {
  let html = '';

  for (const item of items) {
    html += renderItem(item);
  }

  // Add suggestions if we have them
  if (currentSuggestions && currentSuggestionItemId) {
    html += renderSuggestions(currentSuggestions, currentSuggestionItemId);
  }

  itemsFeed.innerHTML = html;
  addCopyButtonListeners();
  addSuggestionListeners();

  if (!userScrolledUp) {
    scrollToBottom();
  }
}

function renderItem(item) {
  const typeClass = `item-${item.type.toLowerCase()}`;
  const typeLabel = getTypeLabel(item.type);

  let content;
  if (item.type === 'Q') {
    content = escapeHtml(item.body || item.title);
  } else {
    content = renderMarkdown(item.body || item.title);
  }

  return `
    <div class="item-container ${typeClass}" data-item-id="${item.id}">
      <span class="item-type-badge">${typeLabel}</span>
      <div class="item-content">${content}</div>
    </div>
  `;
}

function getTypeLabel(type) {
  switch (type) {
    case 'Q': return 'Queue';
    case 'M': return 'Monologue';
    case 'D': return 'Dialogue';
    case 'H': return 'Holologue';
    default: return type;
  }
}

function renderSuggestions(suggestions, itemId) {
  const suggestionsHtml = suggestions.map((s, i) => `
    <button class="suggestion-btn" data-index="${i}" data-item-id="${itemId}" data-prompt="${escapeHtml(s.prompt_text)}">
      ${escapeHtml(s.prompt_text)}
    </button>
  `).join('');

  return `
    <div class="suggestions-container" data-for-item="${itemId}">
      <div class="suggestions-label">Suggestions</div>
      <div class="suggestions-grid">
        ${suggestionsHtml}
      </div>
    </div>
  `;
}

function renderMarkdown(text) {
  if (!text) return '';

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

function addSuggestionListeners() {
  document.querySelectorAll('.suggestion-btn').forEach(btn => {
    btn.addEventListener('click', () => runSuggestion(btn));
  });
}

function scrollToBottom() {
  itemsFeed.scrollTop = itemsFeed.scrollHeight;
}

// Create Queue item
async function createQueueItem() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  isProcessing = true;
  sendBtn.disabled = true;

  // Clear input
  inputEl.value = '';
  inputEl.style.height = 'auto';

  try {
    // Create the Q item
    const res = await fetch('/api/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    });

    const data = await res.json();

    if (data.error) {
      throw new Error(data.error);
    }

    // Add to local list
    items.push(data.item);
    updateCredits();
    updateUI();

    // Fetch suggestions for the new item
    await fetchSuggestions(data.item.id);

  } catch (e) {
    console.error('Create item error:', e);
    // Show error in feed
    items.push({
      id: 'error-' + Date.now(),
      type: 'error',
      title: 'Error',
      body: e.message || 'Failed to create item',
    });
    updateUI();
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
}

async function fetchSuggestions(itemId) {
  try {
    const res = await fetch(`/api/items/${itemId}/suggestions`);
    const data = await res.json();

    if (data.suggestions && data.suggestions.length > 0) {
      currentSuggestions = data.suggestions;
      currentSuggestionItemId = itemId;
      renderItems();
    }
  } catch (e) {
    console.error('Fetch suggestions error:', e);
  }
}

async function runSuggestion(btn) {
  if (isProcessing) return;

  const itemId = btn.dataset.itemId;
  const promptText = btn.dataset.prompt;
  const index = parseInt(btn.dataset.index);

  isProcessing = true;

  // Mark button as running
  btn.classList.add('running');
  btn.disabled = true;
  btn.textContent = 'Running...';

  // Disable other suggestion buttons
  document.querySelectorAll('.suggestion-btn').forEach(b => {
    if (b !== btn) b.disabled = true;
  });

  try {
    const res = await fetch('/api/bonds/run-suggestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_item_ids: [itemId],
        prompt_text: promptText,
        intent_type: currentSuggestions[index]?.intent_type,
        recipe_id: currentSuggestions[index]?.recipe_id,
        output_type: 'M',
      }),
    });

    const data = await res.json();

    if (data.status === 'executed' && data.output_item) {
      // Add the output item
      items.push(data.output_item);

      // Clear suggestions
      currentSuggestions = null;
      currentSuggestionItemId = null;

      updateCredits();
      updateUI();
    } else {
      throw new Error(data.error || 'Failed to run suggestion');
    }

  } catch (e) {
    console.error('Run suggestion error:', e);

    // Show error
    items.push({
      id: 'error-' + Date.now(),
      type: 'error',
      title: 'Error',
      body: e.message || 'Failed to run suggestion',
    });

    // Clear suggestions
    currentSuggestions = null;
    currentSuggestionItemId = null;

    updateUI();
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
}

// Ledger
async function openLedger() {
  ledgerModal.classList.add('visible');
  ledgerContent.innerHTML = '<div class="loading-indicator"><span></span><span></span><span></span></div>';

  try {
    const res = await fetch('/api/ledger');
    const data = await res.json();

    let html = '';

    // Credits
    html += `
      <div class="ledger-section">
        <h3>Credits Balance</h3>
        <div class="ledger-item">
          <strong>${data.credits || 0}</strong> credits remaining
        </div>
      </div>
    `;

    // Items
    html += `
      <div class="ledger-section">
        <h3>Items (${data.items?.length || 0})</h3>
    `;

    if (data.items && data.items.length > 0) {
      for (const item of data.items) {
        const typeClass = `type-${item.type.toLowerCase()}`;
        html += `
          <div class="ledger-item">
            <span class="ledger-item-type ${typeClass}">${item.type}</span>
            ${escapeHtml(item.title)}
          </div>
        `;
      }
    } else {
      html += '<div class="ledger-empty">No items yet</div>';
    }

    html += '</div>';

    // Bonds
    html += `
      <div class="ledger-section">
        <h3>Bonds (${data.bonds?.length || 0})</h3>
    `;

    if (data.bonds && data.bonds.length > 0) {
      for (const bond of data.bonds) {
        html += `
          <div class="ledger-item">
            <span class="ledger-item-type">${bond.status}</span>
            ${escapeHtml(bond.prompt_text?.slice(0, 60) || 'No prompt')}...
          </div>
        `;
      }
    } else {
      html += '<div class="ledger-empty">No bonds yet</div>';
    }

    html += '</div>';

    ledgerContent.innerHTML = html;

  } catch (e) {
    console.error('Ledger error:', e);
    ledgerContent.innerHTML = `<div class="ledger-item item-error">Error loading ledger: ${e.message}</div>`;
  }
}

function closeLedger() {
  ledgerModal.classList.remove('visible');
}

function escapeHtml(str) {
  if (!str) return '';
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
