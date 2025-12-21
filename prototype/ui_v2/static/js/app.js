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
let currentDebugInfo = null;  // Debug info for suggestions (candidate handles)
let isProcessing = false;
let userScrolledUp = false;
let activeItemId = null;  // Track which Q Item is receiving prompts (ontology fix)
let generationMode = 'stub';  // Sprint G2: Track generation mode for UI indicator
let debugMode = false;  // Debug toggle state - shows candidate handles

// Queue Lattice: Hololoop state
let hololoopOptions = null;  // 4 hololoop options for current pair
let hololoopItemA = null;    // First Q item in hololoop pair
let hololoopItemB = null;    // Second Q item in hololoop pair

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

    // Sprint G2: Update generation mode indicator
    if (data.generation_mode) {
      generationMode = data.generation_mode;
      updateGenerationModeIndicator();
    }

    await updateCredits();
  } catch (e) {
    console.error('Init error:', e);
  }
}

// Sprint G2: Update generation mode indicator in header
function updateGenerationModeIndicator() {
  let indicator = document.getElementById('genModeIndicator');
  if (!indicator) {
    // Create indicator element in header
    const headerRight = document.querySelector('.header-right');
    if (headerRight) {
      indicator = document.createElement('div');
      indicator.id = 'genModeIndicator';
      indicator.className = 'gen-mode-indicator';
      headerRight.insertBefore(indicator, headerRight.firstChild);
    }
  }
  if (indicator) {
    const modeText = generationMode.startsWith('openai:')
      ? `GEN=${generationMode.replace('openai:', 'openai:')}`
      : 'GEN=stub';
    indicator.textContent = modeText;
    indicator.className = generationMode.startsWith('openai:')
      ? 'gen-mode-indicator gen-openai'
      : 'gen-mode-indicator gen-stub';
  }
}

// Debug toggle setup
function setupDebugToggle() {
  const headerRight = document.querySelector('.header-right');
  if (!headerRight) return;

  // Create debug toggle button
  const toggle = document.createElement('button');
  toggle.id = 'debugToggle';
  toggle.className = 'debug-toggle';
  toggle.textContent = 'Debug';
  toggle.title = 'Show candidate handles for suggestions';

  toggle.addEventListener('click', () => {
    debugMode = !debugMode;
    toggle.classList.toggle('active', debugMode);

    // Re-render to show/hide debug info
    if (currentSuggestions && currentSuggestionItemId) {
      renderItems();
    }
  });

  // Insert before ledger button
  const ledgerBtn = document.getElementById('ledgerBtn');
  if (ledgerBtn) {
    headerRight.insertBefore(toggle, ledgerBtn);
  } else {
    headerRight.appendChild(toggle);
  }
}

// Sprint G2: Show warning toast
function showWarningToast(message) {
  // Remove any existing toast
  const existing = document.querySelector('.warning-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'warning-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  // Auto-remove after 5 seconds
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
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
      handleComposerSubmit();
    }
  });

  sendBtn.addEventListener('click', handleComposerSubmit);
  newSessionBtn.addEventListener('click', handleNewSession);

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

  // Debug toggle
  setupDebugToggle();

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

    // Render suggestions inline immediately after their parent Q Item (ontology fix)
    if (currentSuggestions && currentSuggestionItemId === item.id) {
      html += renderSuggestions(currentSuggestions, item.id);
    }

    // Queue Lattice: Render hololoop options after the second Q item
    if (hololoopOptions && hololoopItemB && item.id === hololoopItemB.id) {
      html += renderHololoopOptions(hololoopOptions, hololoopItemA, hololoopItemB);
    }
  }

  itemsFeed.innerHTML = html;
  addCopyButtonListeners();
  addSuggestionListeners();
  addHololoopListeners();
  updateActiveItemHighlight();

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
  // Sprint G: Show full bond sentence with handle quote underneath
  // display_text = full bond sentence (no truncation)
  // handle_quote = verbatim substring used (shown in muted text)
  const suggestionsHtml = suggestions.map((s, i) => {
    const displayText = s.display_text || s.prompt_text;  // Fallback if no display_text
    const handleQuote = s.handle_quote || '';  // Handle used for this suggestion
    return `
      <button class="suggestion-btn" data-index="${i}" data-item-id="${itemId}" data-prompt="${escapeHtml(s.prompt_text)}">
        <span class="suggestion-text">${escapeHtml(displayText)}</span>
        ${handleQuote ? `<span class="suggestion-handle">from: "${escapeHtml(handleQuote)}"</span>` : ''}
      </button>
    `;
  }).join('');

  // Debug panel showing candidate handles
  let debugHtml = '';
  if (debugMode && currentDebugInfo) {
    const handles = currentDebugInfo.candidate_handles || [];
    const source = currentDebugInfo.suggestion_source || 'unknown';
    debugHtml = `
      <div class="debug-panel">
        <div class="debug-header">
          <span class="debug-title">Candidate Handles (${handles.length})</span>
          <span class="debug-source">source: ${source}</span>
        </div>
        <div class="debug-handles">
          ${handles.map((h, i) => `<span class="debug-handle">${i + 1}. "${escapeHtml(h)}"</span>`).join('')}
        </div>
      </div>
    `;
  }

  return `
    <div class="suggestions-container" data-for-item="${itemId}">
      <div class="suggestions-label">4 ways to explore this</div>
      ${debugHtml}
      <div class="suggestions-grid">
        ${suggestionsHtml}
      </div>
    </div>
  `;
}

// Queue Lattice: Render hololoop options (bidirectional links)
function renderHololoopOptions(options, itemA, itemB) {
  const titleA = itemA.title || itemA.body?.slice(0, 40) || 'Item A';
  const titleB = itemB.title || itemB.body?.slice(0, 40) || 'Item B';

  const optionsHtml = options.map((opt, i) => {
    return `
      <button class="hololoop-btn" data-index="${opt.option_index}" data-item-a="${itemA.id}" data-item-b="${itemB.id}">
        <span class="hololoop-relation">${escapeHtml(opt.relation_type)}</span>
        <span class="hololoop-forward">A→B: ${escapeHtml(opt.link_text_forward)}</span>
        <span class="hololoop-return">B→A: ${escapeHtml(opt.link_text_return)}</span>
      </button>
    `;
  }).join('');

  return `
    <div class="hololoop-container" data-item-a="${itemA.id}" data-item-b="${itemB.id}">
      <div class="hololoop-header">
        <span class="hololoop-label">Connect these items</span>
        <span class="hololoop-items">"${escapeHtml(titleA.slice(0, 30))}" ↔ "${escapeHtml(titleB.slice(0, 30))}"</span>
      </div>
      <div class="hololoop-grid">
        ${optionsHtml}
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

// Queue Lattice: Hololoop button listeners
function addHololoopListeners() {
  document.querySelectorAll('.hololoop-btn').forEach(btn => {
    btn.addEventListener('click', () => createHololoop(btn));
  });
}

function scrollToBottom() {
  itemsFeed.scrollTop = itemsFeed.scrollHeight;
}

// === Ontology State Management ===
// The UI has two modes:
// 1. NO_ACTIVE_ITEM: Composer creates new Q Items (minting)
// 2. Q_ITEM_ACTIVE: Composer creates D Bonds targeting active Q (generating)

function setActiveItem(itemId) {
  activeItemId = itemId;
  inputEl.placeholder = "Write a prompt for this item...";
}

function clearActiveItem() {
  activeItemId = null;
  currentSuggestions = null;
  currentSuggestionItemId = null;
  currentDebugInfo = null;
  inputEl.placeholder = "Queue something...";
}

function updateActiveItemHighlight() {
  // Remove existing highlights
  document.querySelectorAll('.item-container.active').forEach(el => {
    el.classList.remove('active');
  });

  // Add highlight to active item
  if (activeItemId) {
    const activeEl = document.querySelector(`[data-item-id="${activeItemId}"]`);
    if (activeEl) {
      activeEl.classList.add('active');
    }
  }
}

// === Composer Submit Handler (Ontology-Aware) ===
async function handleComposerSubmit() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  if (activeItemId) {
    // Mode: Active Q Item exists → Create + run D Bond
    await createAndRunDBond(activeItemId, body);
  } else {
    // Mode: No active item → Create new Q Item
    await createQueueItem();
  }
}

// === Create D Bond (User-authored prompt) ===
async function createAndRunDBond(targetItemId, promptText) {
  isProcessing = true;
  sendBtn.disabled = true;

  // Clear input
  inputEl.value = '';
  inputEl.style.height = 'auto';

  try {
    const res = await fetch('/api/bonds/run-suggestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_item_ids: [targetItemId],
        prompt_text: promptText,
        output_type: 'D',  // User-authored = Dialogue (ontology fix)
      }),
    });

    const data = await res.json();

    if (data.status === 'executed' && data.output_item) {
      items.push(data.output_item);
      clearActiveItem();  // Return to NO_ACTIVE_ITEM state
      updateCredits();
      updateUI();
    } else {
      throw new Error(data.error || 'Failed to run bond');
    }

  } catch (e) {
    console.error('Create D Bond error:', e);
    items.push({
      id: 'error-' + Date.now(),
      type: 'error',
      title: 'Error',
      body: e.message || 'Failed to create bond',
    });
    updateUI();
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
}

// === New Session Handler ===
async function handleNewSession() {
  if (confirm('Start fresh? This will clear all items and create a new session.')) {
    try {
      await fetch('/api/reset', { method: 'POST' });
      location.reload();
    } catch (e) {
      console.error('Reset error:', e);
      location.reload();
    }
  }
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

    // Set this Q as the active item (ontology fix)
    setActiveItem(data.item.id);

    // Queue Lattice: Check if we have 2+ Q items to show hololoop options
    const qItems = items.filter(i => i.type === 'Q');
    if (qItems.length >= 2) {
      // Get the two most recent Q items
      const itemB = qItems[qItems.length - 1];  // Just created
      const itemA = qItems[qItems.length - 2];  // Previous Q

      // Fetch hololoop options between them
      await fetchHololoopOptions(itemA.id, itemB.id);
    } else {
      // First Q item - show regular suggestions
      await fetchSuggestions(data.item.id);
    }

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
    // Always fetch with debug=true so we have data if user toggles debug on
    const res = await fetch(`/api/items/${itemId}/suggestions?debug=true`);
    const data = await res.json();

    if (data.suggestions && data.suggestions.length > 0) {
      currentSuggestions = data.suggestions;
      currentSuggestionItemId = itemId;

      // Store debug info for display when debug mode is enabled
      currentDebugInfo = data.debug || null;
      if (currentDebugInfo && data.suggestion_source) {
        currentDebugInfo.suggestion_source = data.suggestion_source;
      }

      renderItems();
    }
  } catch (e) {
    console.error('Fetch suggestions error:', e);
  }
}

// Queue Lattice: Fetch hololoop options for two Q items
async function fetchHololoopOptions(itemAId, itemBId) {
  try {
    const res = await fetch(`/api/hololoop/options?item_a=${itemAId}&item_b=${itemBId}&debug=true`);
    const data = await res.json();

    if (data.options && data.options.length > 0) {
      hololoopOptions = data.options;
      hololoopItemA = items.find(i => i.id === itemAId);
      hololoopItemB = items.find(i => i.id === itemBId);

      // Clear regular suggestions when showing hololoops
      currentSuggestions = null;
      currentSuggestionItemId = null;
      currentDebugInfo = null;

      renderItems();
    }
  } catch (e) {
    console.error('Fetch hololoop options error:', e);
  }
}

// Queue Lattice: Create a hololoop from selected option
async function createHololoop(btn) {
  if (isProcessing) return;

  const optionIndex = parseInt(btn.dataset.index);
  const itemAId = btn.dataset.itemA;
  const itemBId = btn.dataset.itemB;

  isProcessing = true;

  // Mark button as running
  btn.classList.add('running');
  btn.disabled = true;

  // Disable other hololoop buttons
  document.querySelectorAll('.hololoop-btn').forEach(b => {
    if (b !== btn) b.disabled = true;
  });

  try {
    const res = await fetch('/api/hololoop/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_a_id: itemAId,
        item_b_id: itemBId,
        option_index: optionIndex,
      }),
    });

    const data = await res.json();

    if (data.status === 'created') {
      // Clear hololoop state
      hololoopOptions = null;
      hololoopItemA = null;
      hololoopItemB = null;

      // Clear active item state
      clearActiveItem();

      updateUI();

      // Show success message (brief)
      const toast = document.createElement('div');
      toast.className = 'success-toast';
      toast.textContent = `Hololoop created: ${data.hololoop.relation_type}`;
      document.body.appendChild(toast);
      setTimeout(() => {
        toast.classList.add('fade-out');
        setTimeout(() => toast.remove(), 300);
      }, 2000);

    } else {
      throw new Error(data.error || 'Failed to create hololoop');
    }

  } catch (e) {
    console.error('Create hololoop error:', e);
    showWarningToast('Failed to create hololoop: ' + e.message);
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
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

      // Return to NO_ACTIVE_ITEM state (ontology fix)
      clearActiveItem();

      updateCredits();
      updateUI();

      // Sprint G2: Show warning toast if generation fell back to stub
      if (data.generation_warning) {
        showWarningToast(data.generation_warning);
      }
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

    // Return to NO_ACTIVE_ITEM state (ontology fix)
    clearActiveItem();

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
