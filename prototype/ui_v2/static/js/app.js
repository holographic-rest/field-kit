// Field-Kit v0.1 UI - Queue Lattice Sprint
// Version: 2025-01-15-QL2

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
let bonds = [];  // Track hololoop bonds
let currentSuggestions = null;
let currentSuggestionItemId = null;
let currentDebugInfo = null;
let isProcessing = false;
let userScrolledUp = false;
let generationMode = 'stub';
let debugMode = false;

// Queue Lattice: Active Item state
let activeItemId = null;  // The currently active (clicked/focused) Q item

// Queue Lattice: Draft Hololoop state
let draftHololoop = null;  // Current draft hololoop bond
let draftHololoopOptions = null;  // Available options for regeneration

// UI Version (for cache busting)
const UI_VERSION = '2025-01-15-QL2';

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
  // Add version stamp to header
  const headerRight = document.querySelector('.header-right');
  if (headerRight) {
    const stamp = document.createElement('span');
    stamp.className = 'version-stamp';
    stamp.textContent = `v${UI_VERSION}`;
    stamp.title = 'UI Version';
    headerRight.insertBefore(stamp, headerRight.firstChild);
  }
}

async function checkAndInit() {
  try {
    // Cache-busting timestamp
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

function setupDebugToggle() {
  const headerRight = document.querySelector('.header-right');
  if (!headerRight) return;

  const toggle = document.createElement('button');
  toggle.id = 'debugToggle';
  toggle.className = 'debug-toggle';
  toggle.textContent = 'Debug';
  toggle.title = 'Show candidate handles';

  toggle.addEventListener('click', () => {
    debugMode = !debugMode;
    toggle.classList.toggle('active', debugMode);
    renderItems();
  });

  const ledgerBtn = document.getElementById('ledgerBtn');
  if (ledgerBtn) {
    headerRight.insertBefore(toggle, ledgerBtn);
  } else {
    headerRight.appendChild(toggle);
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

    // Find any draft hololoops
    const drafts = bonds.filter(b => b.bond_kind === 'hololoop' && b.status === 'draft');
    if (drafts.length > 0) {
      draftHololoop = drafts[drafts.length - 1];  // Most recent
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
  const qItems = items.filter(i => i.type === 'Q');

  for (const item of items) {
    html += renderItem(item);
  }

  // Render draft hololoop section if exists
  if (draftHololoop && qItems.length >= 2) {
    html += renderDraftHololoopSection();
  } else if (qItems.length === 1) {
    html += renderGatingHint();
  }

  itemsFeed.innerHTML = html;
  addItemClickListeners();
  addHandleListeners();
  addDraftHololoopListeners();
  updateActiveItemHighlight();

  if (!userScrolledUp) {
    scrollToBottom();
  }
}

function renderItem(item) {
  const typeClass = `item-${item.type.toLowerCase()}`;
  const typeLabel = getTypeLabel(item.type);
  const isActive = item.id === activeItemId;
  const activeClass = isActive ? 'active' : '';

  let content;
  if (item.type === 'Q') {
    content = escapeHtml(item.body || item.title);
  } else {
    content = renderMarkdown(item.body || item.title);
  }

  // Queue Lattice: Render handles for Q items
  let handlesHtml = '';
  if (item.type === 'Q' && item.handles && item.handles.length > 0) {
    handlesHtml = renderItemHandles(item.id, item.handles);
  }

  // Check if this item is part of the draft hololoop
  let hololinkHtml = '';
  if (draftHololoop && item.type === 'Q') {
    const inputIds = draftHololoop.input_item_ids || [];
    if (inputIds.includes(item.id)) {
      hololinkHtml = renderItemHololink(item.id, draftHololoop);
    }
  }

  return `
    <div class="item-container ${typeClass} ${activeClass}" data-item-id="${item.id}">
      <div class="item-header">
        <span class="item-type-badge">${typeLabel}</span>
        ${item.type === 'Q' ? `<button class="item-focus-btn" data-item-id="${item.id}" title="Set as active">⊙</button>` : ''}
      </div>
      <div class="item-content">${content}</div>
      ${handlesHtml}
      ${hololinkHtml}
    </div>
  `;
}

function renderItemHandles(itemId, handles) {
  const handleChips = handles.map((h, i) => {
    const starredClass = h.starred ? 'starred' : '';
    return `
      <span class="handle-chip ${starredClass}" data-item-id="${itemId}" data-index="${i}">
        <span class="handle-text">"${escapeHtml(h.quote.substring(0, 40))}${h.quote.length > 40 ? '...' : ''}"</span>
        <button class="handle-star" title="${h.starred ? 'Unstar' : 'Star'}">★</button>
      </span>
    `;
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
  const targetId = isSource ? inputIds[1] : inputIds[0];
  const direction = isSource ? '→' : '←';

  return `
    <div class="item-hololink" data-bond-id="${bond.id}">
      <span class="hololink-arrow">${direction}</span>
      <span class="hololink-text">${escapeHtml(linkText || 'Link pending...')}</span>
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
        <span class="draft-label">Draft Hololoop</span>
        <span class="draft-status">pending acceptance</span>
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
      <div class="draft-actions">
        <button class="draft-btn accept" data-action="accept">Accept</button>
        <button class="draft-btn edit" data-action="edit">Edit</button>
        <button class="draft-btn regenerate" data-action="regenerate">Regenerate</button>
        <button class="draft-btn change-target" data-action="change-target">Change Target</button>
      </div>
    </div>
  `;
}

function renderGatingHint() {
  return `
    <div class="gating-hint">
      <span class="gating-icon">🔗</span>
      <span class="gating-text">Create one more Item to auto-generate a draft hololoop.</span>
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

// Item interaction listeners
function addItemClickListeners() {
  // Focus button clicks
  document.querySelectorAll('.item-focus-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.stopPropagation();
      setActiveItem(btn.dataset.itemId);
    });
  });

  // Item container clicks (for Q items)
  document.querySelectorAll('.item-container.item-q').forEach(container => {
    container.addEventListener('click', () => {
      setActiveItem(container.dataset.itemId);
    });
  });

  // Copy buttons
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

function addHandleListeners() {
  document.querySelectorAll('.handle-star').forEach(btn => {
    btn.addEventListener('click', async (e) => {
      e.stopPropagation();
      const chip = btn.closest('.handle-chip');
      const itemId = chip.dataset.itemId;
      const index = parseInt(chip.dataset.index);
      await toggleHandleStar(itemId, index);
    });
  });
}

async function toggleHandleStar(itemId, handleIndex) {
  const item = items.find(i => i.id === itemId);
  if (!item || !item.handles) return;

  const handles = [...item.handles];
  handles[handleIndex].starred = !handles[handleIndex].starred;

  try {
    const res = await fetch(`/api/items/${itemId}/handles`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ handles }),
    });

    if (res.ok) {
      item.handles = handles;
      renderItems();
    }
  } catch (e) {
    console.error('Toggle star error:', e);
  }
}

function addDraftHololoopListeners() {
  document.querySelectorAll('.draft-actions .draft-btn').forEach(btn => {
    btn.addEventListener('click', async () => {
      const action = btn.dataset.action;
      const section = btn.closest('.draft-hololoop-section');
      const bondId = section?.dataset.bondId;

      if (!bondId) return;

      switch (action) {
        case 'accept':
          await acceptDraftHololoop(bondId);
          break;
        case 'edit':
          showEditHololoopModal(bondId);
          break;
        case 'regenerate':
          await regenerateDraftHololoop(bondId);
          break;
        case 'change-target':
          showChangeTargetModal(bondId);
          break;
      }
    });
  });
}

async function acceptDraftHololoop(bondId) {
  try {
    const res = await fetch(`/api/draft-hololoop/${bondId}/accept`, {
      method: 'POST',
    });

    if (res.ok) {
      draftHololoop = null;
      showSuccessToast('Hololoop accepted!');
      await loadBonds();
      renderItems();
    }
  } catch (e) {
    console.error('Accept draft error:', e);
    showWarningToast('Failed to accept hololoop');
  }
}

async function regenerateDraftHololoop(bondId) {
  try {
    const res = await fetch(`/api/draft-hololoop/${bondId}/regenerate`, {
      method: 'POST',
    });

    const data = await res.json();
    if (data.options && data.options.length > 0) {
      // Update draft with first option
      const selected = data.options[0];
      await fetch(`/api/draft-hololoop/${bondId}/update`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          link_text_forward: selected.link_text_forward,
          link_text_return: selected.link_text_return,
        }),
      });

      draftHololoopOptions = data.options;
      await loadBonds();
      renderItems();
      showSuccessToast('Regenerated hololink options');
    }
  } catch (e) {
    console.error('Regenerate error:', e);
    showWarningToast('Failed to regenerate');
  }
}

function showEditHololoopModal(bondId) {
  // Simple inline edit for now - could be modal
  const bond = bonds.find(b => b.id === bondId);
  if (!bond) return;

  const newForward = prompt('Edit A→B link text:', bond.link_text_forward);
  if (newForward === null) return;

  const newReturn = prompt('Edit B→A link text:', bond.link_text_return);
  if (newReturn === null) return;

  updateDraftHololoop(bondId, { link_text_forward: newForward, link_text_return: newReturn });
}

async function showChangeTargetModal(bondId) {
  const bond = bonds.find(b => b.id === bondId);
  if (!bond) return;

  const sourceId = bond.input_item_ids[0];
  const qItems = items.filter(i => i.type === 'Q' && i.id !== sourceId);

  if (qItems.length === 0) {
    showWarningToast('No other items available as targets');
    return;
  }

  // Simple prompt for now
  const options = qItems.map((item, i) => `${i + 1}. ${item.title?.substring(0, 40)}`).join('\n');
  const choice = prompt(`Select new target:\n${options}\n\nEnter number:`);

  if (choice === null) return;

  const idx = parseInt(choice) - 1;
  if (idx >= 0 && idx < qItems.length) {
    await updateDraftHololoop(bondId, { target_item_id: qItems[idx].id });
    // Need to regenerate after changing target
    await regenerateDraftHololoop(bondId);
  }
}

async function updateDraftHololoop(bondId, updates) {
  try {
    const res = await fetch(`/api/draft-hololoop/${bondId}/update`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });

    if (res.ok) {
      await loadBonds();
      renderItems();
    }
  } catch (e) {
    console.error('Update draft error:', e);
  }
}

// Active Item management
function setActiveItem(itemId) {
  activeItemId = itemId;
  inputEl.placeholder = "Write a prompt for this item...";
  updateActiveItemHighlight();
}

function clearActiveItem() {
  activeItemId = null;
  currentSuggestions = null;
  currentSuggestionItemId = null;
  currentDebugInfo = null;
  inputEl.placeholder = "Queue something...";
  updateActiveItemHighlight();
}

function updateActiveItemHighlight() {
  document.querySelectorAll('.item-container.active').forEach(el => {
    el.classList.remove('active');
  });

  if (activeItemId) {
    const activeEl = document.querySelector(`[data-item-id="${activeItemId}"]`);
    if (activeEl) {
      activeEl.classList.add('active');
    }
  }
}

// Composer submit handler
async function handleComposerSubmit() {
  const body = inputEl.value.trim();
  if (!body || isProcessing) return;

  if (activeItemId) {
    await createAndRunDBond(activeItemId, body);
  } else {
    await createQueueItem();
  }
}

async function createAndRunDBond(targetItemId, promptText) {
  isProcessing = true;
  sendBtn.disabled = true;
  inputEl.value = '';
  inputEl.style.height = 'auto';

  try {
    const res = await fetch('/api/bonds/run-suggestion', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        input_item_ids: [targetItemId],
        prompt_text: promptText,
        output_type: 'D',
      }),
    });

    const data = await res.json();

    if (data.status === 'executed' && data.output_item) {
      items.push(data.output_item);
      clearActiveItem();
      updateCredits();
      updateUI();
    } else {
      throw new Error(data.error || 'Failed to run bond');
    }

  } catch (e) {
    console.error('Create D Bond error:', e);
    showWarningToast('Failed to create bond: ' + e.message);
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
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

// Create Queue item
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

    // Queue Lattice: Auto-create draft hololoop on 2nd+ Q item
    const qItems = items.filter(i => i.type === 'Q');

    if (qItems.length >= 2 && !draftHololoop) {
      // Auto-create draft hololoop
      await createDraftHololoop(data.item.id, activeItemId);
    }

    // Set new item as active
    setActiveItem(data.item.id);
    updateUI();

  } catch (e) {
    console.error('Create item error:', e);
    showWarningToast('Failed to create item: ' + e.message);
  }

  isProcessing = false;
  sendBtn.disabled = !inputEl.value.trim();
  inputEl.focus();
}

async function createDraftHololoop(sourceItemId, targetItemId) {
  try {
    const res = await fetch('/api/draft-hololoop', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        source_item_id: sourceItemId,
        target_item_id: targetItemId || null,  // Will auto-find if null
      }),
    });

    const data = await res.json();

    if (data.status === 'draft_created') {
      draftHololoop = data.bond;
      draftHololoopOptions = data.all_options;
      showSuccessToast('Draft hololoop created!');
      await loadBonds();
    }
  } catch (e) {
    console.error('Create draft hololoop error:', e);
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

    // Bonds (including hololoops)
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
            ${escapeHtml(bond.prompt_text?.slice(0, 60) || bond.link_text_forward?.slice(0, 60) || 'No text')}...
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
