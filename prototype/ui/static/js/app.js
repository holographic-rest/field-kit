/**
 * Field-Kit v0.1 UI JavaScript
 *
 * Flow-first UI: ChatGPT-like but creates Queue items with suggestions.
 * No frameworks - vanilla JS only.
 *
 * Type terminology:
 *   Q = Queue (user input)
 *   M = Monologue (system-suggested bond output)
 *   D = Dialogue (user-prompted bond output)
 *   H = Holologue (many-to-one synthesis)
 */

// Type labels (Q = Queue, not Question)
const TYPE_LABELS = {
    Q: 'Queue',
    M: 'Monologue',
    D: 'Dialogue',
    H: 'Holologue',
};

// === State ===
const state = {
    initialized: false,
    networkId: null,
    episodeId: null,
    credits: 0,
    items: [],
    bonds: [],
    selectedItemIds: new Set(),
    currentBondId: null,
    ledgerData: null,
    selectedLedgerItem: null,
    tutorialStarted: false,
    lastCreatedItemId: null,
    itemSuggestions: {}, // item_id -> suggestions array
    isRunning: false,
};

// === DOM Elements ===
const els = {
    // Header
    episodeLabel: document.getElementById('episodeLabel'),
    creditsChip: document.getElementById('creditsChip'),
    ledgerBtn: document.getElementById('ledgerBtn'),

    // Tutorial
    tutorialBanner: document.getElementById('tutorialBanner'),
    dismissTutorialBtn: document.getElementById('dismissTutorialBtn'),

    // Field
    field: document.getElementById('field'),
    fieldContent: document.getElementById('fieldContent'),
    emptyState: document.getElementById('emptyState'),
    itemsList: document.getElementById('itemsList'),
    jumpToLatest: document.getElementById('jumpToLatest'),

    // Ephemeral card
    ephemeralCard: document.getElementById('ephemeralCard'),
    ephemeralStatus: document.getElementById('ephemeralStatus'),
    ephemeralContent: document.getElementById('ephemeralContent'),

    // Bottom composer
    bottomComposer: document.getElementById('bottomComposer'),
    composerInput: document.getElementById('composerInput'),
    composerSubmit: document.getElementById('composerSubmit'),

    // Holologue bar
    hololoqueBar: document.getElementById('hololoqueBar'),
    hololoqueSelectedCount: document.getElementById('hololoqueSelectedCount'),
    runHololoqueBtn: document.getElementById('runHololoqueBtn'),

    // Holologue modal
    hololoqueModal: document.getElementById('hololoqueModal'),
    closeHololoqueModal: document.getElementById('closeHololoqueModal'),
    hololoqueModalInfo: document.getElementById('hololoqueModalInfo'),
    artifactKind: document.getElementById('artifactKind'),
    cancelHololoqueBtn: document.getElementById('cancelHololoqueBtn'),
    confirmHololoqueBtn: document.getElementById('confirmHololoqueBtn'),

    // Ledger drawer
    ledgerDrawer: document.getElementById('ledgerDrawer'),
    closeLedgerBtn: document.getElementById('closeLedgerBtn'),
    ledgerItems: document.getElementById('ledgerItems'),
    ledgerBonds: document.getElementById('ledgerBonds'),
    ledgerEpisodes: document.getElementById('ledgerEpisodes'),
    ledgerEvents: document.getElementById('ledgerEvents'),
    curatedItems: document.getElementById('curatedItems'),
    curatedBonds: document.getElementById('curatedBonds'),
    curatedWarnings: document.getElementById('curatedWarnings'),
    jsonPreview: document.getElementById('jsonPreview'),
    itemCount: document.getElementById('itemCount'),
    bondCount: document.getElementById('bondCount'),
    episodeCount: document.getElementById('episodeCount'),
    eventNameFilter: document.getElementById('eventNameFilter'),
    eventQdpiFilter: document.getElementById('eventQdpiFilter'),
    copyJsonBtn: document.getElementById('copyJsonBtn'),
    exportEpisodeBtn: document.getElementById('exportEpisodeBtn'),
    exportCuratedBtn: document.getElementById('exportCuratedBtn'),

    // Operator drawer
    operatorDrawer: document.getElementById('operatorDrawer'),
    operatorTitle: document.getElementById('operatorTitle'),
    closeOperatorBtn: document.getElementById('closeOperatorBtn'),

    // Operator modes
    editorMode: document.getElementById('editorMode'),
    runStateMode: document.getElementById('runStateMode'),

    // Editor mode
    editorInputItems: document.getElementById('editorInputItems'),
    promptText: document.getElementById('promptText'),
    cancelEditorBtn: document.getElementById('cancelEditorBtn'),
    runBondBtn: document.getElementById('runBondBtn'),

    // Run state mode
    runModeLabel: document.getElementById('runModeLabel'),
    runInputsLabel: document.getElementById('runInputsLabel'),
    runStatusText: document.getElementById('runStatusText'),

    // Toast
    toast: document.getElementById('toast'),
    toastMessage: document.getElementById('toastMessage'),
    toastAction: document.getElementById('toastAction'),
};

// === API Functions ===
async function api(endpoint, options = {}) {
    const url = `/api${endpoint}`;
    const config = {
        headers: { 'Content-Type': 'application/json' },
        ...options,
    };
    if (options.body && typeof options.body === 'object') {
        config.body = JSON.stringify(options.body);
    }
    const response = await fetch(url, config);
    return response.json();
}

// === Initialization ===
async function init() {
    const status = await api('/status');

    if (!status.initialized) {
        const result = await api('/init', { method: 'POST' });
        state.initialized = true;
        state.networkId = result.network_id;
        state.episodeId = result.episode_id;
        state.credits = result.credits;
    } else {
        state.initialized = true;
        state.networkId = status.network_id;
        state.episodeId = status.episode_id;
        state.credits = status.credits;
    }

    updateHeader();
    await loadItems();
    setupEventListeners();

    // Focus the composer
    els.composerInput.focus();
}

// === Header Updates ===
function updateHeader() {
    els.episodeLabel.textContent = `Episode: ${state.episodeId ? state.episodeId.slice(0, 12) + '...' : 'Loading...'}`;
    updateCredits(state.credits);
}

function updateCredits(newBalance, flash = false) {
    const oldBalance = state.credits;
    state.credits = newBalance;
    els.creditsChip.textContent = `Credits: ${newBalance}`;

    if (flash && oldBalance !== newBalance) {
        const flashClass = newBalance > oldBalance ? 'flash-plus' : 'flash-minus';
        els.creditsChip.classList.add(flashClass);
        setTimeout(() => els.creditsChip.classList.remove(flashClass), 500);
    }
}

// === Tutorial ===
function dismissTutorial() {
    els.tutorialBanner.style.display = 'none';
}

async function startTutorial() {
    if (!state.tutorialStarted) {
        await api('/tutorial/start', { method: 'POST' });
        state.tutorialStarted = true;
        els.tutorialBanner.style.display = 'flex';
    }
}

// === Items ===
async function loadItems() {
    const result = await api('/items');
    state.items = result.items || [];
    renderItems();
    updateComposerVisibility();
}

function updateComposerVisibility() {
    // Always show composer
    els.bottomComposer.style.display = 'flex';

    // Update empty state
    if (state.items.length === 0) {
        els.emptyState.style.display = 'flex';
        els.itemsList.style.display = 'none';
    } else {
        els.emptyState.style.display = 'none';
        els.itemsList.style.display = 'flex';
    }
}

function renderItems() {
    if (state.items.length === 0) {
        els.emptyState.style.display = 'flex';
        els.itemsList.style.display = 'none';
        return;
    }

    els.emptyState.style.display = 'none';
    els.itemsList.style.display = 'flex';

    els.itemsList.innerHTML = state.items.map(item => {
        const isSelected = state.selectedItemIds.has(item.id);
        const suggestions = state.itemSuggestions[item.id] || [];
        const showSuggestions = item.type === 'Q' && suggestions.length > 0;

        return `
            <div class="item-card ${isSelected ? 'selected' : ''}" data-id="${item.id}">
                <div class="item-header">
                    <span class="item-type type-${item.type}" title="${TYPE_LABELS[item.type]}">${item.type}</span>
                    <span class="item-title">${escapeHtml(item.title)}</span>
                    <span class="item-select-indicator">${isSelected ? '✓' : ''}</span>
                </div>
                ${item.body ? `<div class="item-body">${escapeHtml(item.body.slice(0, 300))}${item.body.length > 300 ? '...' : ''}</div>` : ''}
                <div class="item-meta">
                    <span class="item-id">${item.id.slice(0, 16)}...</span>
                    <span>${formatTime(item.created_at)}</span>
                </div>
                ${showSuggestions ? renderInlineSuggestions(item.id, suggestions) : ''}
            </div>
        `;
    }).join('');

    // Add click handlers for item cards
    els.itemsList.querySelectorAll('.item-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't trigger if clicking on a suggestion
            if (e.target.closest('.inline-suggestion')) return;
            handleItemClick(card.dataset.id, e);
        });
    });

    // Add click handlers for inline suggestions
    els.itemsList.querySelectorAll('.inline-suggestion').forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.stopPropagation();
            const itemId = btn.dataset.itemId;
            const prompt = btn.dataset.prompt;
            const intent = btn.dataset.intent;
            const recipe = btn.dataset.recipe;
            runSuggestionOneClick(itemId, prompt, intent, recipe);
        });
    });

    updateHololoqueBar();
}

function renderInlineSuggestions(itemId, suggestions) {
    return `
        <div class="inline-suggestions">
            ${suggestions.map(s => `
                <button class="inline-suggestion"
                        data-item-id="${itemId}"
                        data-prompt="${escapeHtml(s.prompt_text)}"
                        data-intent="${s.intent_type || ''}"
                        data-recipe="${s.recipe_id || ''}">
                    <span class="suggestion-recipe">${s.recipe_id || s.intent_type || 'suggest'}</span>
                    <span class="suggestion-text">${escapeHtml(truncate(s.prompt_text, 60))}</span>
                </button>
            `).join('')}
        </div>
    `;
}

function handleItemClick(itemId, e) {
    const isMultiSelect = e.shiftKey || e.metaKey || e.ctrlKey;

    if (isMultiSelect) {
        if (state.selectedItemIds.has(itemId)) {
            state.selectedItemIds.delete(itemId);
        } else {
            state.selectedItemIds.add(itemId);
        }
    } else {
        if (state.selectedItemIds.has(itemId) && state.selectedItemIds.size === 1) {
            // Deselect if already the only selection
            state.selectedItemIds.clear();
        } else {
            state.selectedItemIds.clear();
            state.selectedItemIds.add(itemId);
        }
    }

    renderItems();
    updateHololoqueBar();
}

// === Bottom Composer (creates Q items or D bonds) ===
async function handleComposerSubmit() {
    const text = els.composerInput.value.trim();
    if (!text || state.isRunning) return;

    // If items exist and one is selected, treat as custom bond prompt -> D output
    if (state.items.length > 0) {
        await runCustomBondFromComposer(text);
    } else {
        // First item: create Q
        await createQueueItem(text);
    }
}

async function createQueueItem(text) {
    state.isRunning = true;
    els.composerInput.disabled = true;
    els.composerSubmit.disabled = true;

    // Extract title from first line (up to 40 chars)
    const lines = text.split('\n').filter(l => l.trim());
    const title = truncate(lines[0] || text, 40);
    const body = text;

    const result = await api('/items', {
        method: 'POST',
        body: { title, body, type: 'Q' },
    });

    els.composerInput.value = '';
    els.composerInput.style.height = 'auto';

    await loadItems();
    updateCredits(result.credits, true);

    // Start tutorial on first item
    if (!state.tutorialStarted) {
        await startTutorial();
    }

    // Load suggestions for the new item
    state.lastCreatedItemId = result.item.id;
    await loadSuggestionsForItem(result.item.id);

    scrollToBottom();
    showToast('Saved ✓ · View Ledger', true);

    state.isRunning = false;
    els.composerInput.disabled = false;
    els.composerSubmit.disabled = false;
    els.composerInput.focus();
}

async function runCustomBondFromComposer(promptText) {
    // Determine input items
    let inputItemIds;
    if (state.selectedItemIds.size > 0) {
        inputItemIds = Array.from(state.selectedItemIds);
    } else {
        // Use most recent Q item as default input
        const qItems = state.items.filter(i => i.type === 'Q');
        if (qItems.length > 0) {
            inputItemIds = [qItems[qItems.length - 1].id];
        } else {
            inputItemIds = [state.items[state.items.length - 1].id];
        }
    }

    state.isRunning = true;
    els.composerInput.disabled = true;
    els.composerSubmit.disabled = true;

    // Show ephemeral card
    showEphemeralCard('Generating...');

    // Create and run bond with D output
    const result = await api('/bonds/run-suggestion', {
        method: 'POST',
        body: {
            input_item_ids: inputItemIds,
            prompt_text: promptText,
            output_type: 'D',  // Custom prompts produce D
        },
    });

    hideEphemeralCard();
    els.composerInput.value = '';
    els.composerInput.style.height = 'auto';

    if (result.status === 'executed') {
        await loadItems();
        updateCredits(result.credits, true);
        state.selectedItemIds.clear();
        renderItems();
        scrollToBottom();
        showToast('Saved ✓ · View Ledger', true);
    } else {
        showToast('Bond execution failed', false);
    }

    state.isRunning = false;
    els.composerInput.disabled = false;
    els.composerSubmit.disabled = false;
    els.composerInput.focus();
}

// === Suggestions ===
async function loadSuggestionsForItem(itemId) {
    const result = await api(`/items/${itemId}/suggestions`);
    state.itemSuggestions[itemId] = result.suggestions || [];
    renderItems();
}

async function runSuggestionOneClick(itemId, promptText, intentType, recipeId) {
    if (state.isRunning) return;
    state.isRunning = true;

    // Show ephemeral card
    showEphemeralCard('Generating...');

    // One-click: create bond + run -> M output
    const result = await api('/bonds/run-suggestion', {
        method: 'POST',
        body: {
            input_item_ids: [itemId],
            prompt_text: promptText,
            intent_type: intentType || null,
            recipe_id: recipeId || null,
            output_type: 'M',  // Suggestions produce M
        },
    });

    hideEphemeralCard();

    if (result.status === 'executed') {
        // Clear suggestions for this item (they've been used)
        delete state.itemSuggestions[itemId];

        await loadItems();
        updateCredits(result.credits, true);
        scrollToBottom();
        showToast('Saved ✓ · View Ledger', true);
    } else {
        showToast('Bond execution failed', false);
    }

    state.isRunning = false;
}

// === Prompt Editor (drawer) ===
function openPromptEditor(itemIds, prompt = '', intent = null, recipe = null) {
    setOperatorMode('editor');
    els.operatorTitle.textContent = 'Edit Prompt';

    // Show selected items
    const selectedItems = state.items.filter(i => itemIds.includes(i.id));
    els.editorInputItems.innerHTML = selectedItems.map(item => `
        <div class="input-item">
            <span class="item-type type-${item.type}" title="${TYPE_LABELS[item.type]}">${item.type}</span>
            <span>${escapeHtml(truncate(item.title, 30))}</span>
        </div>
    `).join('');

    els.promptText.value = prompt;
    els.promptText.dataset.intent = intent || '';
    els.promptText.dataset.recipe = recipe || '';
    els.promptText.dataset.itemIds = JSON.stringify(itemIds);

    openOperatorDrawer();
    setTimeout(() => els.promptText.focus(), 100);
}

async function runBondFromEditor() {
    const prompt = els.promptText.value.trim();
    if (!prompt || state.isRunning) return;

    const itemIds = JSON.parse(els.promptText.dataset.itemIds || '[]');
    if (itemIds.length === 0) {
        showToast('No input items selected');
        return;
    }

    const intent = els.promptText.dataset.intent || null;
    const recipe = els.promptText.dataset.recipe || null;
    const outputType = document.querySelector('input[name="outputType"]:checked')?.value || 'M';

    state.isRunning = true;
    setOperatorMode('runState');
    els.runModeLabel.textContent = 'Running Bond...';
    els.runInputsLabel.textContent = `Inputs: ${itemIds.length}`;

    showEphemeralCard('Generating...');

    const result = await api('/bonds/run-suggestion', {
        method: 'POST',
        body: {
            input_item_ids: itemIds,
            prompt_text: prompt,
            intent_type: intent,
            recipe_id: recipe,
            output_type: outputType,
        },
    });

    hideEphemeralCard();

    if (result.status === 'executed') {
        await loadItems();
        updateCredits(result.credits, true);
        state.selectedItemIds.clear();
        renderItems();
        scrollToBottom();
        closeOperatorDrawer();
        showToast('Saved ✓ · View Ledger', true);
    } else {
        showToast('Bond execution failed', false);
        setOperatorMode('editor');
    }

    state.isRunning = false;
}

// === Holologue ===
function updateHololoqueBar() {
    const count = state.selectedItemIds.size;
    if (count >= 2) {
        els.hololoqueBar.style.display = 'flex';
        els.hololoqueSelectedCount.textContent = `${count} items selected`;
    } else {
        els.hololoqueBar.style.display = 'none';
    }
}

function openHololoqueModal() {
    const count = state.selectedItemIds.size;
    if (count < 2) {
        showToast('Select at least 2 items for Holologue');
        return;
    }
    els.hololoqueModalInfo.textContent = `Synthesize ${count} items into one output.`;
    els.hololoqueModal.classList.add('open');
}

function closeHololoqueModal() {
    els.hololoqueModal.classList.remove('open');
}

async function runHolologue() {
    const selectedItemIds = Array.from(state.selectedItemIds);
    const artifactKind = els.artifactKind.value;

    if (selectedItemIds.length < 2) {
        showToast('Select at least 2 items for Holologue');
        return;
    }

    closeHololoqueModal();
    state.isRunning = true;

    showEphemeralCard('Synthesizing...');

    const result = await api('/holologue/run', {
        method: 'POST',
        body: {
            selected_item_ids: selectedItemIds,
            artifact_kind: artifactKind,
        },
    });

    hideEphemeralCard();

    if (result.status === 'completed') {
        // Store proposals as suggestions for the H item
        if (result.proposals && result.proposals.length > 0) {
            state.itemSuggestions[result.output_item.id] = result.proposals;
        }

        await loadItems();
        updateCredits(result.credits, true);
        state.selectedItemIds.clear();
        renderItems();
        scrollToBottom();
        showToast('Saved ✓ · View Ledger', true);
    } else {
        showToast(result.error || 'Holologue failed', false);
    }

    state.isRunning = false;
}

// === Ephemeral Card ===
function showEphemeralCard(status) {
    els.ephemeralCard.style.display = 'block';
    els.ephemeralStatus.textContent = status;
    els.ephemeralContent.innerHTML = '<div class="shimmer"></div>';
    scrollToBottom();
}

function hideEphemeralCard() {
    els.ephemeralCard.style.display = 'none';
}

// === Ledger ===
async function openLedger() {
    els.ledgerDrawer.classList.add('open');
    els.field.classList.add('ledger-open');

    const result = await api('/ledger');
    state.ledgerData = result;
    renderLedger();
}

function closeLedger() {
    els.ledgerDrawer.classList.remove('open');
    els.field.classList.remove('ledger-open');
}

function renderLedger() {
    if (!state.ledgerData) return;

    const { items, bonds, episodes, events, curated } = state.ledgerData;

    els.itemCount.textContent = items.length;
    els.bondCount.textContent = bonds.length;
    els.episodeCount.textContent = episodes.length;

    els.ledgerItems.innerHTML = items.map(i => `
        <div class="ledger-item" data-type="item" data-id="${i.id}">
            <span class="ledger-item-id">${i.id.slice(0, 16)}...</span>
            <span class="ledger-item-label">${i.type} (${TYPE_LABELS[i.type]}): ${escapeHtml(truncate(i.title, 25))}</span>
        </div>
    `).join('') || '<div class="ledger-item">No items</div>';

    els.ledgerBonds.innerHTML = bonds.map(b => `
        <div class="ledger-item" data-type="bond" data-id="${b.id}">
            <span class="ledger-item-id">${b.id.slice(0, 16)}...</span>
            <span class="ledger-item-label">${b.status}: ${escapeHtml(truncate(b.prompt_text, 20))}</span>
        </div>
    `).join('') || '<div class="ledger-item">No bonds</div>';

    els.ledgerEpisodes.innerHTML = episodes.map(e => `
        <div class="ledger-item" data-type="episode" data-id="${e.id}">
            <span class="ledger-item-id">${e.id.slice(0, 16)}...</span>
            <span class="ledger-item-label">${escapeHtml(e.title)}</span>
        </div>
    `).join('') || '<div class="ledger-item">No episodes</div>';

    const eventNames = [...new Set(events.map(e => e.name))];
    els.eventNameFilter.innerHTML = '<option value="">All events</option>' +
        eventNames.map(name => `<option value="${name}">${name}</option>`).join('');

    renderEvents(events);

    els.curatedItems.innerHTML = (curated.curated_items || []).map(i => `
        <div class="ledger-item" data-type="item" data-id="${i.id}">
            <span class="ledger-item-id">${i.id.slice(0, 16)}...</span>
            <span class="ledger-item-label">${i.type}: ${escapeHtml(truncate(i.title, 25))}</span>
        </div>
    `).join('') || '<div class="ledger-item">(none)</div>';

    els.curatedBonds.innerHTML = (curated.curated_bonds || []).map(b => `
        <div class="ledger-item" data-type="bond" data-id="${b.id}">
            <span class="ledger-item-id">${b.id.slice(0, 16)}...</span>
            <span class="ledger-item-label">${b.status}</span>
        </div>
    `).join('') || '<div class="ledger-item">(none)</div>';

    if (curated.warnings && curated.warnings.length > 0) {
        els.curatedWarnings.style.display = 'block';
        els.curatedWarnings.innerHTML = curated.warnings.map(w => `<div>⚠ ${escapeHtml(w)}</div>`).join('');
    } else {
        els.curatedWarnings.style.display = 'none';
    }

    document.querySelectorAll('.ledger-item[data-id]').forEach(item => {
        item.addEventListener('click', () => {
            selectLedgerItem(item.dataset.type, item.dataset.id);
        });
    });
}

function renderEvents(events) {
    const nameFilter = els.eventNameFilter.value;
    const qdpiFilter = els.eventQdpiFilter.value;

    let filtered = events;
    if (nameFilter) filtered = filtered.filter(e => e.name === nameFilter);
    if (qdpiFilter) filtered = filtered.filter(e => e.qdpi === qdpiFilter);

    els.ledgerEvents.innerHTML = filtered.map(e => `
        <div class="ledger-item event-item" data-type="event" data-id="${e.id}">
            <span class="event-seq">#${e.seq}</span>
            <span class="event-name">${e.name}</span>
            <div class="event-meta">
                <span>qdpi: ${e.qdpi} (${TYPE_LABELS[e.qdpi] || e.qdpi})</span>
                <span>${e.direction}</span>
            </div>
        </div>
    `).join('') || '<div class="ledger-item">No events</div>';

    els.ledgerEvents.querySelectorAll('.event-item').forEach(item => {
        item.addEventListener('click', () => {
            selectLedgerItem('event', item.dataset.id);
        });
    });
}

function selectLedgerItem(type, id) {
    document.querySelectorAll('.ledger-item.selected').forEach(el => {
        el.classList.remove('selected');
    });

    const item = document.querySelector(`.ledger-item[data-id="${id}"]`);
    if (item) item.classList.add('selected');

    let data = null;
    if (state.ledgerData) {
        if (type === 'item') data = state.ledgerData.items.find(i => i.id === id);
        else if (type === 'bond') data = state.ledgerData.bonds.find(b => b.id === id);
        else if (type === 'episode') data = state.ledgerData.episodes.find(e => e.id === id);
        else if (type === 'event') data = state.ledgerData.events.find(e => e.id === id);
    }

    state.selectedLedgerItem = data;
    updateJsonPreview(data);
    switchTab('json');
}

function updateJsonPreview(data) {
    els.jsonPreview.textContent = data ? JSON.stringify(data, null, 2) : 'Select an object to view JSON';
}

async function copyJson() {
    if (state.selectedLedgerItem) {
        await navigator.clipboard.writeText(JSON.stringify(state.selectedLedgerItem, null, 2));
        showToast('JSON copied to clipboard');
    }
}

async function exportEpisode() {
    const result = await api('/export/episode');
    downloadJson(result, `episode_export_${new Date().toISOString().slice(0, 10)}.json`);
    showToast('Episode exported');
}

async function exportCurated() {
    const result = await api('/export/curated');
    downloadJson(result, `curated_export_${new Date().toISOString().slice(0, 10)}.json`);
    showToast('Curated projection exported');
}

function downloadJson(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

// === Drawers ===
function openOperatorDrawer() {
    els.operatorDrawer.classList.add('open');
    els.field.classList.add('operator-open');
}

function closeOperatorDrawer() {
    els.operatorDrawer.classList.remove('open');
    els.field.classList.remove('operator-open');
}

function setOperatorMode(mode) {
    els.editorMode.classList.remove('active');
    els.runStateMode.classList.remove('active');

    if (mode === 'editor') els.editorMode.classList.add('active');
    else if (mode === 'runState') els.runStateMode.classList.add('active');
}

// === Tabs ===
function switchTab(tabName) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    document.querySelectorAll('.tab-panel').forEach(panel => {
        panel.classList.toggle('active', panel.id === tabName + 'Panel');
    });
}

// === Toast ===
function showToast(message, showAction = false) {
    els.toastMessage.textContent = message;
    els.toastAction.style.display = showAction ? 'inline' : 'none';
    els.toast.classList.add('show');
    setTimeout(() => els.toast.classList.remove('show'), 3000);
}

// === Utilities ===
function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.slice(0, maxLen) + '...' : str;
}

function formatTime(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = (now - date) / 1000;

    if (diff < 60) return 'just now';
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return date.toLocaleDateString();
}

function scrollToBottom() {
    setTimeout(() => {
        els.fieldContent.scrollTop = els.fieldContent.scrollHeight;
    }, 100);
}

// === Auto-resize textarea ===
function autoResize(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

// === Event Listeners ===
function setupEventListeners() {
    // Header
    els.ledgerBtn.addEventListener('click', () => {
        if (els.ledgerDrawer.classList.contains('open')) closeLedger();
        else openLedger();
    });

    // Tutorial
    els.dismissTutorialBtn.addEventListener('click', dismissTutorial);

    // Bottom composer
    els.composerInput.addEventListener('input', () => autoResize(els.composerInput));
    els.composerInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleComposerSubmit();
        }
    });
    els.composerSubmit.addEventListener('click', handleComposerSubmit);

    // Holologue
    els.runHololoqueBtn.addEventListener('click', openHololoqueModal);
    els.closeHololoqueModal.addEventListener('click', closeHololoqueModal);
    els.cancelHololoqueBtn.addEventListener('click', closeHololoqueModal);
    els.confirmHololoqueBtn.addEventListener('click', runHolologue);
    els.hololoqueModal.addEventListener('click', (e) => {
        if (e.target === els.hololoqueModal) closeHololoqueModal();
    });

    // Ledger drawer
    els.closeLedgerBtn.addEventListener('click', closeLedger);

    // Ledger tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
    });

    // Event filters
    els.eventNameFilter.addEventListener('change', () => {
        if (state.ledgerData) renderEvents(state.ledgerData.events);
    });
    els.eventQdpiFilter.addEventListener('change', () => {
        if (state.ledgerData) renderEvents(state.ledgerData.events);
    });

    // JSON actions
    els.copyJsonBtn.addEventListener('click', copyJson);
    els.exportEpisodeBtn.addEventListener('click', exportEpisode);
    els.exportCuratedBtn.addEventListener('click', exportCurated);

    // Operator drawer
    els.closeOperatorBtn.addEventListener('click', closeOperatorDrawer);
    els.cancelEditorBtn.addEventListener('click', closeOperatorDrawer);
    els.runBondBtn.addEventListener('click', runBondFromEditor);

    // Toast action
    els.toastAction.addEventListener('click', openLedger);

    // Keyboard shortcuts
    document.addEventListener('keydown', (e) => {
        // L - Toggle ledger
        if (e.key === 'l' && !e.metaKey && !e.ctrlKey && !isInputFocused()) {
            e.preventDefault();
            if (els.ledgerDrawer.classList.contains('open')) closeLedger();
            else openLedger();
        }

        // Escape - Close modal/drawer
        if (e.key === 'Escape') {
            if (els.hololoqueModal.classList.contains('open')) closeHololoqueModal();
            else if (els.operatorDrawer.classList.contains('open')) closeOperatorDrawer();
            else if (els.ledgerDrawer.classList.contains('open')) closeLedger();
        }

        // Cmd+Enter - Run bond (in editor)
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            if (els.editorMode.classList.contains('active')) {
                e.preventDefault();
                runBondFromEditor();
            }
        }
    });

    // Scroll detection for "Jump to latest"
    els.fieldContent.addEventListener('scroll', () => {
        const { scrollTop, scrollHeight, clientHeight } = els.fieldContent;
        const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;
        els.jumpToLatest.style.display = isNearBottom ? 'none' : 'block';
    });

    els.jumpToLatest.addEventListener('click', scrollToBottom);
}

function isInputFocused() {
    const active = document.activeElement;
    return active && (active.tagName === 'INPUT' || active.tagName === 'TEXTAREA' || active.tagName === 'SELECT');
}

// === Init ===
document.addEventListener('DOMContentLoaded', init);
