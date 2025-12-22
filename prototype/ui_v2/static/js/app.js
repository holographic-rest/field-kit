// Field-Kit v0.1 UI - Queue Lattice (Hololoop Only)
// Version: 2025-01-15-QL3
// IMPORTANT: This UI creates Queue items ONLY. No D/M/H output generation.

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
let bonds = [];
let isProcessing = false;
let userScrolledUp = false;
let generationMode = 'stub';

// Queue Lattice state
let hololoopOptions = null;      // 4 hololoop options when available
let hololoopItemA = null;        // First Q item in pair
let hololoopItemB = null;        // Second Q item in pair
let draftHololoop = null;        // Created hololoop bond (after selection)

// UI Version
const UI_VERSION = '2025-01-15-QL3';

// Initialize
init();

async function init() {
  setupEventListeners();
  setupVersionStamp();
  await checkAndInit();
  await loadItems();
  await loadBonds();
  updateUI();
  inputEl.focus();
}

function setupVersionStamp() {
  const headerRight = document.querySelector('.header-right');
  if (headerRight) {
    const stamp = document.createElement('span');
    stamp.className = 'version-stamp';
    stamp.textContent = `v${UI_VERSION}`;
    stamp.title = 'Queue Lattice UI';
    headerRight.insertBefore(stamp, headerRight.firstChild);
  }
}

async function checkAndInit() {
  try {
    const ts = Date.now();
    const res = await fetch(`/api/status?_t=${ts}`);
    const data = await res.json();

    if (!data.initialized) {
      await fetch('/api/init', { method: 'POST' });
    }

    if (data.generation_mode) {
      generationMode = data.generation_mode;
      updateGenerationModeIndicator();
    }

    await updateCredits();
  } catch (e) {
    console.error('Init error:', e);
  }
}

function updateGenerationModeIndicator() {
  let indicator = document.getElementById('genModeIndicator');
  if (!indicator) {
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
      ? `GEN=${generationMode}`
      : 'GEN=stub';
    indicator.textContent = modeText;
    indicator.className = generationMode.startsWith('openai:')
      ? 'gen-mode-indicator gen-openai'
      : 'gen-mode-indicator gen-stub';
  }
}

function showWarningToast(message) {
  const existing = document.querySelector('.warning-toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = 'warning-toast';
  toast.textContent = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 5000);
}

function showSuccessToast(message) {
  const toast = document.createElement('div');
  toast.className = 'success-toast';
  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    toast.classList.add('fade-out');
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

async function loadItems() {
  try {
    const ts = Date.now();
    const res = await fetch(`/api/items?_t=${ts}`);
    const data = await res.json();
    items = data.items || [];
  } catch (e) {
    console.error('Load items error:', e);
    items = [];
  }
}

async function loadBonds() {
  try {
    const ts = Date.now();
    const res = await fetch(`/api/bonds?_t=${ts}`);
    const data = await res.json();
    bonds = data.bonds || [];

    // Find any existing hololoop
    const hololoops = bonds.filter(b => b.bond_kind === 'hololoop');
    if (hololoops.length > 0) {
      draftHololoop = hololoops[hololoops.length - 1];
    }
  } catch (e) {
    console.error('Load bonds error:', e);
    bonds = [];
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
  const qItems = items.filter(i => i.type === 'Q');

  for (const item of items) {
    html += renderItem(item);
  }

  // Queue Lattice: Show appropriate state based on Q item count
  if (qItems.length === 1 && !draftHololoop) {
    // After Q1: Show gating hint
    html += renderGatingHint();
  } else if (qItems.length >= 2 && hololoopOptions && !draftHololoop) {
    // After Q2: Show 4 hololoop options for selection
    html += renderHololoopOptions();
  } else if (draftHololoop) {
    // After selection: Show draft hololoop
    html += renderDraftHololoopSection();
  }

  itemsFeed.innerHTML = html;
  addCopyButtonListeners();
  addHololoopOptionListeners();
  addDraftHololoopListeners();

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

  // Show handles if available
  let handlesHtml = '';
  if (item.type === 'Q' && item.handles && item.handles.length > 0) {
    handlesHtml = renderItemHandles(item.handles);
  }

  // Show hololink if this item is part of draft hololoop
  let hololinkHtml = '';
  if (draftHololoop && item.type === 'Q') {
    const inputIds = draftHololoop.input_item_ids || [];
    if (inputIds.includes(item.id)) {
      hololinkHtml = renderItemHololink(item.id, draftHololoop);
    }
  }

  return `
    <div class="item-container ${typeClass}" data-item-id="${item.id}">
      <div class="item-header">
        <span class="item-type-badge">${typeLabel}</span>
      </div>
      <div class="item-content">${content}</div>
      ${handlesHtml}
      ${hololinkHtml}
    </div>
  `;
}

function renderItemHandles(handles) {
  const handleChips = handles.slice(0, 5).map(h => {
    const text = h.quote.length > 40 ? h.quote.substring(0, 40) + '...' : h.quote;
    const starredClass = h.starred ? 'starred' : '';
    return `<span class="handle-chip ${starredClass}">"${escapeHtml(text)}"</span>`;
  }).join('');

  return `
    <div class="item-handles">
      <div class="handles-label">Handles:</div>
      <div class="handles-list">${handleChips}</div>
    </div>
  `;
}

function renderItemHololink(itemId, bond) {
  const inputIds = bond.input_item_ids || [];
  const isSource = inputIds[0] === itemId;
  const linkText = isSource ? bond.link_text_forward : bond.link_text_return;
  const direction = isSource ? '→' : '←';

  return `
    <div class="item-hololink">
      <span class="hololink-arrow">${direction}</span>
      <span class="hololink-text">${escapeHtml(linkText || 'Link pending...')}</span>
    </div>
  `;
}

function renderGatingHint() {
  return `
    <div class="gating-hint">
      <span class="gating-icon">🔗</span>
      <span class="gating-text">Create one more Item to generate hololoop options.</span>
    </div>
  `;
}

function renderHololoopOptions() {
  if (!hololoopOptions || hololoopOptions.length === 0) return '';

  const itemA = items.find(i => i.id === hololoopItemA);
  const itemB = items.find(i => i.id === hololoopItemB);
  const nameA = itemA?.title?.substring(0, 25) || 'Item A';
  const nameB = itemB?.title?.substring(0, 25) || 'Item B';

  const optionsHtml = hololoopOptions.map((opt, idx) => `
    <button class="hololoop-option-btn" data-option-index="${idx}">
      <div class="hololoop-option-content">
        <div class="hololoop-direction">
          <span class="direction-label">${escapeHtml(nameA)} →</span>
          <span class="direction-text">${escapeHtml(opt.link_text_forward)}</span>
        </div>
        <div class="hololoop-direction">
          <span class="direction-label">${escapeHtml(nameB)} →</span>
          <span class="direction-text">${escapeHtml(opt.link_text_return)}</span>
        </div>
      </div>
    </button>
  `).join('');

  return `
    <div class="hololoop-options-container">
      <div class="hololoop-options-header">
        <span class="hololoop-options-title">Choose a hololoop connection</span>
        <span class="hololoop-options-subtitle">${escapeHtml(nameA)} ↔ ${escapeHtml(nameB)}</span>
      </div>
      <div class="hololoop-options-grid">
        ${optionsHtml}
      </div>
    </div>
  `;
}

function renderDraftHololoopSection() {
  if (!draftHololoop) return '';

  const inputIds = draftHololoop.input_item_ids || [];
  const sourceItem = items.find(i => i.id === inputIds[0]);
  const targetItem = items.find(i => i.id === inputIds[1]);

  if (!sourceItem || !targetItem) return '';

  const sourceName = sourceItem.title?.substring(0, 30) || 'Source';
  const targetName = targetItem.title?.substring(0, 30) || 'Target';

  return `
    <div class="draft-hololoop-section" data-bond-id="${draftHololoop.id}">
      <div class="draft-header">
        <span class="draft-label">Hololoop Created</span>
        <span class="draft-status">${draftHololoop.status}</span>
      </div>
      <div class="draft-items">
        <span class="draft-item">${escapeHtml(sourceName)}</span>
        <span class="draft-connector">↔</span>
        <span class="draft-item">${escapeHtml(targetName)}</span>
      </div>
      <div class="draft-links">
        <div class="draft-link">
          <span class="link-direction">→</span>
          <span class="link-text">${escapeHtml(draftHololoop.link_text_forward || '')}</span>
        </div>
        <div class="draft-link">
          <span class="link-direction">←</span>
          <span class="link-text">${escapeHtml(draftHololoop.link_text_return || '')}</span>
        </div>
      </div>
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

function renderMarkdown(text) {
  if (!text) return '';

  let html = marked.parse(text);

  html = html.replace(/<pre><code([^>]*)>([\s\S]*?)<\/code><\/pre>/g, (match, attrs, code) => {
    return `<div class="code-block-wrapper"><button class="copy-btn">Copy</button><pre><code${attrs}>${code}</code></pre></div>`;
  });

  return html;
}

// Listeners
function addCopyButtonListeners() {
  document.querySelectorAll('.copy-btn').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
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

function addHololoopOptionListeners() {
  document.querySelectorAll('.hololoop-option-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const optionIndex = parseInt(btn.dataset.optionIndex);
      await selectHololoopOption(optionIndex);
    });
  });
}

async function selectHololoopOption(optionIndex) {
  if (!hololoopOptions || !hololoopItemA || !hololoopItemB) return;

  isProcessing = true;

  try {
    // Create hololoop bond with selected option
    const res = await fetch('/api/hololoop/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        item_a_id: hololoopItemA,
        item_b_id: hololoopItemB,
        option_index: optionIndex + 1,  // API uses 1-indexed
      }),
    });

    const data = await res.json();

    if (data.status === 'created' && data.bond) {
      draftHololoop = data.bond;
      hololoopOptions = null;  // Clear options after selection
      showSuccessToast('Hololoop created!');
      await loadBonds();
      renderItems();
    } else {
      throw new Error(data.error || 'Failed to create hololoop');
    }
  } catch (e) {
    console.error('Select hololoop error:', e);
    showWarningToast('Failed to create hololoop: ' + e.message);
  }

  isProcessing = false;
}

function addDraftHololoopListeners() {
  // No actions needed for now - draft is created by selection
}

// Composer - ONLY creates Queue items (no D/M generation)
async function handleComposerSubmit() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  // Queue Lattice: ALWAYS create Queue items only
  await createQueueItem();
}

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

// Create Queue item (the ONLY item creation path)
async function createQueueItem() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  isProcessing = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  try {
    const res = await fetch('/api/items', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ body }),
    });

    const data = await res.json();

    if (data.error) {
      throw new Error(data.error);
    }

    items.push(data.item);
    updateCredits();

    // Queue Lattice: After Q2+, fetch hololoop options (NOT auto-create)
    const qItems = items.filter(i => i.type === 'Q');

    if (qItems.length >= 2 && !draftHololoop) {
      // Fetch 4 hololoop options for user to select
      await fetchHololoopOptions(qItems[qItems.length - 2].id, qItems[qItems.length - 1].id);
    }

    updateUI();

  } catch (e) {
    console.error('Create item error:', e);
    showWarningToast('Failed to create item: ' + e.message);
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
}

async function fetchHololoopOptions(itemAId, itemBId) {
  try {
    const res = await fetch(`/api/hololoop/options?item_a=${itemAId}&item_b=${itemBId}`);
    const data = await res.json();

    if (data.options && data.options.length > 0) {
      hololoopOptions = data.options;
      hololoopItemA = itemAId;
      hololoopItemB = itemBId;
    }
  } catch (e) {
    console.error('Fetch hololoop options error:', e);
  }
}

function scrollToBottom() {
  itemsFeed.scrollTop = itemsFeed.scrollHeight;
}

// Ledger modal
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
        const kindBadge = bond.bond_kind === 'hololoop' ? ' [hololoop]' : '';
        html += `
          <div class="ledger-item">
            <span class="ledger-item-type">${bond.status}${kindBadge}</span>
            ${escapeHtml(bond.link_text_forward?.slice(0, 60) || bond.prompt_text?.slice(0, 60) || 'No text')}...
          </div>
        `;
      }
    } else {
      html += '<div class="ledger-empty">No bonds yet</div>';
    }

    html += '</div>';

    // Events summary
    if (data.events && data.events.length > 0) {
      html += `
        <div class="ledger-section">
          <h3>Recent Events (${data.events.length})</h3>
      `;

      const recentEvents = data.events.slice(-10);
      for (const event of recentEvents) {
        html += `
          <div class="ledger-item ledger-event">
            <span class="ledger-item-type">${event.name}</span>
            seq=${event.seq}
          </div>
        `;
      }

      html += '</div>';
    }

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
