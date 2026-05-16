const socket = io();
let currentSessionId = null;
let currentAiMessageId = null;
let isGenerating = false;
let autoScroll = true;
let attachedImageBase64 = null;
let activeProjectId = null;
let selectedIds = new Set();
let mediaRecorder = null;
let audioChunks = [];
let attachedFile = null;
let currentUserId = null;
let config = { temperature: 0.7 };

// SVG Icons (no emojis)
const ICONS = {
    gear: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
    search: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/></svg>',
    close: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
    pin: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2L15.09 8.26L22 9.27L17 14.14L18.18 21.02L12 17.77L5.82 21.02L7 14.14L2 9.27L8.91 8.26L12 2z"/></svg>',
    archive: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"/></svg>',
    unarchive: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8M8 12h4l-3-3m0 0l-3 3m3-3v6"/></svg>',
    star: '<svg class="w-4 h-4" fill="currentColor" viewBox="0 0 24 24"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
    starOutline: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>',
    pencil: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"/></svg>',
    document: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>',
    logout: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>',
    clipboard: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2"/></svg>',
    tool: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>',
    check: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>',
    xmark: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>',
    warning: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"/></svg>',
    plus: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"/></svg>',
    trash: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/></svg>',
    history: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>'
};

$(document).ready(function () {
    loadModels();
    loadHistoryList();
    loadSettings();
    loadLibrary();
    loadProjects();
    loadGroups();
    loadAllTags();
    checkAuth();

    const params = new URLSearchParams(window.location.search);
    const sessionParam = params.get('session');
    if (sessionParam) {
        setTimeout(() => loadSession(sessionParam), 300);
    }

    $('#chat-form').on('submit', handleFormSubmit);
    $('#project-form').on('submit', handleProjectSubmit);

    $('#user-input').on('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleFormSubmit(e); }
    });

    document.getElementById('user-input').addEventListener('paste', handlePaste);
    const dz = document.getElementById('user-input');
    dz.addEventListener('dragover', (e) => { e.preventDefault(); $(dz).addClass('border-nothing-red') });
    dz.addEventListener('dragleave', (e) => { e.preventDefault(); $(dz).removeClass('border-nothing-red') });
    dz.addEventListener('drop', (e) => { e.preventDefault(); $(dz).removeClass('border-nothing-red'); if (e.dataTransfer.files[0]) handleChatFileDrop(e.dataTransfer.files[0]); });

    $('#history-search').on('keyup', filterHistory);
    $('#bulk-delete-btn').on('click', bulkDeleteSelected);
    $('#select-all-btn').on('click', toggleSelectAll);
    socket.on('title_updated', () => loadHistoryList());

    $(document).on('click', function (e) {
        if (!$(e.target).closest('.msg-bubble, .action-bar').length) {
            $('.action-bar').addClass('hidden');
        }
    });

    function runSearch() {
        const q = $('#search-input').val().trim();
        if (q.length < 2) { $('#search-results').empty(); return; }
        const model = $('#search-model-filter').val();
        const project = $('#search-project-filter').val();
        const dateFrom = $('#search-date-from').val();
        const dateTo = $('#search-date-to').val();
        let url = `/api/search?q=${encodeURIComponent(q)}`;
        if (model) url += `&model=${encodeURIComponent(model)}`;
        if (project) url += `&project_id=${encodeURIComponent(project)}`;
        if (dateFrom) url += `&date_from=${encodeURIComponent(dateFrom)}`;
        if (dateTo) url += `&date_to=${encodeURIComponent(dateTo)}`;
        $.get(url, (data) => {
            const el = $('#search-results'); el.empty();
            if (!data.length) { el.append('<div class="text-gray-500 text-xs p-4 text-center">No results</div>'); return; }
            data.forEach(m => {
                el.append(`<div class="bg-[#151515] p-3 rounded border border-white/5 hover:border-white/20 cursor-pointer" onclick="loadSession('${m.session_id}');toggleSearchModal();"><div class="text-[10px] text-gray-500 font-mono mb-1">${escapeHtml(m.session_title)} · ${escapeHtml(m.model || '')} · ${m.role.toUpperCase()} · ${timeAgo(m.timestamp)}</div><div class="text-xs text-gray-300 line-clamp-2">${escapeHtml(m.content.substring(0, 200))}</div></div>`);
            });
        });
    }

    $('#search-input').on('keyup', runSearch);
    $('#search-model-filter, #search-project-filter, #search-date-from, #search-date-to').on('change', runSearch);

    // Keyboard shortcuts
    $(document).on('keydown', function (e) {
        if (e.ctrlKey && e.key === 'k') { e.preventDefault(); toggleSearchModal(); }
        if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newChat(); }
        if (e.ctrlKey && e.key === 'l') { e.preventDefault(); toggleLibrary(); }
        if (e.ctrlKey && e.shiftKey && e.key === 'E') { e.preventDefault(); exportChat('md'); }
        if (e.ctrlKey && e.key === 'f' && currentSessionId) { e.preventDefault(); toggleSessionSearch(); }
        if (e.ctrlKey && e.key === 'd') { e.preventDefault(); toggleTheme(); }
    });

    // Theme restoration
    const savedAccent = localStorage.getItem('ln-accent');
    const savedFontSize = localStorage.getItem('ln-font-size');
    if (savedAccent) applyAccentColor(savedAccent);
    if (savedFontSize) $('body').css('font-size', savedFontSize);

    // Audio recording
    if (navigator.mediaDevices) {
        $('#record-btn').on('click', toggleRecording);
    }
});


// --- TOAST ---
function showToast(msg, type = 'info') {
    const colors = { info: 'border-blue-500', success: 'border-green-500', error: 'border-red-500', warning: 'border-yellow-500' };
    const cls = colors[type] || colors.info;
    const existing = $('.toast-notification');
    if (existing.length > 3) existing.first().remove();
    const el = $(`<div class="toast-notification fixed top-4 right-4 z-[100] bg-[#1a1a1a] border-l-4 ${cls} border-white/10 text-white text-xs font-mono px-4 py-3 rounded shadow-2xl animate-fade-in max-w-sm">${escapeHtml(msg)}</div>`);
    $('body').append(el);
    setTimeout(() => { el.css('opacity', '0'); setTimeout(() => el.remove(), 300); }, 3000);
}


function timeAgo(ts) {
    if (!ts) return '';
    const diff = Date.now() - new Date(ts + 'Z').getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return mins + 'm ago';
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return hrs + 'h ago';
    const days = Math.floor(hrs / 24);
    return days + 'd ago';
}

function estimateTokens(text) {
    if (!text) return 0;
    return Math.ceil(text.length / 4);
}


// --- SEARCH ---
function toggleSearchModal() {
    $('#search-modal').toggleClass('hidden');
    if (!$('#search-modal').hasClass('hidden')) {
        $('#search-input').val('').focus();
        $('#search-results').empty();
        // Populate model filter
        const sel = $('#search-model-filter');
        const currentVal = sel.val();
        sel.empty().append('<option value="">All models</option>');
        $('#model-select option').each(function () {
            const v = $(this).val();
            if (v && v !== 'Loading...' && v !== 'Ollama Down') sel.append(`<option value="${v}">${v}</option>`);
        });
        sel.val(currentVal);
        // Populate project filter
        const pSel = $('#search-project-filter');
        const currentP = pSel.val();
        pSel.empty().append('<option value="">All projects</option>');
        $.get('/api/projects', (projects) => {
            projects.forEach(p => pSel.append(`<option value="${p.id}">${escapeHtml(p.title)}</option>`));
            pSel.val(currentP);
        });
    }
}


// --- MODEL MANAGER ---
function toggleModelModal() { $('#model-modal').toggleClass('hidden'); loadModelList(); }

function loadModelList() {
    const el = $('#model-list');
    el.html('<div class="text-gray-500 text-xs p-2">Loading...</div>');
    $.get('/api/models/manage', (data) => {
        el.empty();
        if (!data || data.length === 0) { el.append('<div class="text-gray-500 text-xs p-2 text-center">No models installed</div>'); return; }
        data.forEach(m => {
            el.append(`<div class="bg-[#151515] p-3 rounded border border-white/5 flex justify-between items-center"><div><div class="text-sm text-white font-mono">${m.name}</div><div class="text-[10px] text-gray-500">${m.details ? m.details.family + ' · ' + m.details.parameter_size : ''}</div></div><button onclick="deleteModel('${m.name}')" class="text-gray-600 hover:text-red-500 px-2 text-lg">×</button></div>`);
        });
    }).fail(() => { el.html('<div class="text-red-500 text-xs p-2 text-center">Ollama is not running</div>'); });
}

function pullModel() {
    const name = $('#new-model-name').val().trim();
    if (!name) return;
    const btn = $('#model-modal').find('button:contains("Pull")');
    btn.prop('disabled', true).text('Pulling...');
    $.ajax({
        url: '/api/models/pull', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ name }),
        success: () => { loadModelList(); $('#new-model-name').val(''); showToast(`Model "${name}" pulled`, 'success'); },
        error: (e) => { showToast("Failed: " + (e.responseJSON?.error || e.statusText), 'error'); },
        complete: () => { btn.prop('disabled', false).text('Pull'); }
    });
}

function deleteModel(name) {
    if (!confirm(`Delete model "${name}"?`)) return;
    $.ajax({
        url: `/api/models/${encodeURIComponent(name)}`, type: 'DELETE',
        success: () => { loadModelList(); loadModels(); },
        error: (e) => { showToast("Failed: " + (e.responseJSON?.error || e.statusText), 'error'); }
    });
}


// --- DOCUMENT MANAGER ---
function toggleDocModal() {
    if (!$('#doc-modal').hasClass('hidden')) { $('#doc-modal').addClass('hidden'); return; }
    if (!activeProjectId) { showToast("Select a project first.", 'warning'); return; }
    $('#doc-modal').removeClass('hidden');
    const el = $('#doc-list');
    el.html('<div class="text-gray-500 text-xs p-2">Loading...</div>');
    $.get(`/api/projects/${activeProjectId}/documents`, (data) => {
        el.empty();
        if (!data.length) { el.append('<div class="text-gray-500 text-xs p-4 text-center">No documents in this project</div>'); return; }
        data.forEach(d => {
            el.append(`<div class="bg-[#151515] p-3 rounded border border-white/5 flex justify-between items-center"><div><div class="text-sm text-white font-mono truncate max-w-[300px]">${escapeHtml(d.filename)}</div><div class="text-[10px] text-gray-500">${(d.size / 1024).toFixed(1)} KB</div></div><button onclick="deleteDoc(${d.id})" class="text-gray-600 hover:text-red-500 px-2 text-lg">×</button></div>`);
        });
    });
}

function deleteDoc(id) {
    if (!confirm('Delete this document?')) return;
    $.ajax({ url: `/api/documents/${id}`, type: 'DELETE', success: () => { toggleDocModal(); showToast("Deleted.", 'success'); } });
}


// --- GROUPS ---
function loadGroups() {
    $.get('/api/groups', (data) => {
        const sel = $('#group-select');
        sel.empty().append('<option value="">No group</option>');
        data.forEach(g => sel.append(`<option value="${g.id}">${escapeHtml(g.title)}</option>`));
    });
}

function createGroup() {
    const title = prompt("Group name:");
    if (!title) return;
    $.ajax({
        url: '/api/groups', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ title }),
        success: () => { loadGroups(); showToast('Group created', 'success'); }
    });
}

function deleteGroup(gid) {
    if (!confirm('Delete group? Sessions stay but become ungrouped.')) return;
    $.ajax({ url: `/api/groups/${gid}`, type: 'DELETE', success: () => { loadGroups(); loadHistoryList(); } });
}

function setSessionGroup(sid, gid) {
    $.ajax({
        url: '/api/sessions/group', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ session_id: sid, group_id: gid || null })
    });
}


// --- URL SCRAPER ---
function scrapeUrl() {
    const url = $('#project-url').val().trim();
    if (!url) return;
    const status = $('#url-status');
    status.removeClass('hidden').text('Scraping...');
    $.ajax({
        url: '/api/urlscrape', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ url }),
        success: (res) => {
            if (res.content) {
                const blob = new File([res.content], `scraped-${Date.now()}.txt`, { type: 'text/plain' });
                const dt = new DataTransfer();
                dt.items.add(blob);
                const fileInput = $('input[name="files"]')[0];
                if (fileInput) {
                    const existing = fileInput.files;
                    for (let i = 0; i < existing.length; i++) dt.items.add(existing[i]);
                    fileInput.files = dt.files;
                }
                status.text(`✓ Scraped ${res.content.length} chars from URL`).addClass('text-green-500').removeClass('text-gray-600');
            }
        },
        error: (e) => { status.text('✗ Scrape failed: ' + (e.responseJSON?.error || e.statusText)).addClass('text-red-500').removeClass('text-gray-600'); }
    });
}

// --- PROJECTS ---
function toggleProjectModal() { $('#project-modal').toggleClass('hidden'); }

function handleProjectSubmit(e) {
    e.preventDefault();
    const btn = $(this).find('button[type="submit"]');
    btn.prop('disabled', true).text('Creating...');
    const formData = new FormData(this);
    const url = $('#project-url').val().trim();
    if (url) formData.append('url', url);
    $.ajax({
        url: '/api/projects', type: 'POST', data: formData, contentType: false, processData: false,
        success: (res) => {
            if (res.status === 'success') {
                toggleProjectModal();
                loadProjects();
                selectProject(res.id, formData.get('title'));
                this.reset();
                $('#project-url').val('');
            } else { showToast("Error: " + res.message, 'error'); }
        },
        error: (err) => { showToast("Upload Failed.", 'error'); console.error(err); },
        complete: () => { btn.prop('disabled', false).text('Create Project'); }
    });
}

function loadProjects() {
    $.get('/api/projects', (data) => {
        $('#projects-list').empty();
        data.forEach(p => {
            $('#projects-list').append(`<div onclick="selectProject('${p.id}', '${escapeHtml(p.title)}')" class="project-tag cursor-pointer bg-[#222] border border-white/5 px-2 py-1 rounded text-[10px] text-gray-400 hover:text-white hover:border-nothing-red truncate max-w-[100px] transition" title="${escapeHtml(p.title)}">${escapeHtml(p.title)}</div>`);
        });
    });
}

function selectProject(pid, title) {
    activeProjectId = pid;
    $('#active-project-name').text(`PROJECT: ${title}`).removeClass('hidden');
    $('.project-tag').removeClass('border-nothing-red text-white').addClass('text-gray-400 border-white/5');
    newChat(true);
}

function exitProject() {
    activeProjectId = null;
    $('#active-project-name').addClass('hidden');
    newChat(false);
}


// --- MESSAGING ---
function handleFormSubmit(e) {
    e.preventDefault();
    if (isGenerating) { socket.emit('stop_generation', { session_id: currentSessionId }); setGeneratingState(false); return; }
    sendMessage();
}

function getModelOptions() {
    return {
        top_p: $('#param-top-p').val(),
        top_k: $('#param-top-k').val(),
        repeat_penalty: $('#param-repeat-penalty').val(),
        max_tokens: $('#param-max-tokens').val(),
    };
}

function sendMessage(overridePrompt = null, isEdit = false, msgId = null) {
    const $input = $('#user-input');
    let prompt = overridePrompt || $input.val().trim();
    const model = $('#model-select').val();
    if ((!prompt && !attachedImageBase64)) return;
    if (!model) { showToast("Select a model first.", 'warning'); return; }
    $('#welcome-msg').addClass('hidden');
    let tempId = `temp-${Date.now()}`;
    const imgToSend = attachedImageBase64;

    // Handle /file command
    let fileContext = null;
    if (prompt.startsWith('/file ')) {
        const filePath = prompt.replace('/file ', '').trim();
        prompt = `Read the contents of the file at ${filePath} and answer based on it.`;
        $.ajax({
            url: '/api/file/read', type: 'POST', contentType: 'application/json',
            data: JSON.stringify({ path: filePath }), async: false,
            success: (res) => {
                if (res.content) {
                    fileContext = { filename: res.filename, content: res.content };
                    showToast(`Loaded file: ${res.filename}`, 'success');
                }
            },
            error: (e) => {
                showToast('File read failed: ' + (e.responseJSON?.error || e.statusText), 'error');
            }
        });
    }

    // Include attached file if present
    if (!fileContext && attachedFile) {
        fileContext = { filename: attachedFile.name, content: attachedFile.content };
    }

    if (!isEdit) {
        $input.val('').css('height', 'auto');
        $input.focus();
        appendMessage('user', prompt, tempId, null, imgToSend);
        if (attachedImageBase64) clearImage();
        if (attachedFile) clearAttachedFile();
    }
    currentAiMessageId = `msg-${Date.now()}`;
    appendMessage('ai', '', currentAiMessageId);
    setGeneratingState(true);

    let enrichedPrompt = prompt;
    if (prompt.startsWith('/search ')) {
        const searchQuery = prompt.replace('/search ', '');
        enrichedPrompt = `[Web Search Results for "${searchQuery}"]\n`;
        $.ajax({
            url: '/api/websearch', type: 'POST', contentType: 'application/json',
            data: JSON.stringify({ query: searchQuery }), async: false,
            success: (res) => {
                if (res.results && res.results.length) {
                    enrichedPrompt += res.results.map((r, i) => `${i + 1}. ${r.snippet}\n   Source: ${r.url}`).join('\n') + '\n\n';
                } else { enrichedPrompt += 'No results found.\n\n'; }
                enrichedPrompt += `User question: ${searchQuery}`;
            }, error: () => { enrichedPrompt = prompt; }
        });
    }

    socket.emit('user_message', {
        prompt: enrichedPrompt, model: model, session_id: currentSessionId,
        project_id: activeProjectId,
        system_prompt: config.custom_session_prompt || null,
        temperature: config.temperature,
        options: getModelOptions(),
        is_edit: isEdit, msg_id: msgId, temp_id: tempId,
        images: imgToSend ? [imgToSend] : [],
        file_context: fileContext,
        user_id: currentUserId
    });
    config.custom_session_prompt = null;
}

function triggerRegenerate() {
    if (!currentSessionId || isGenerating) return;
    const lastMsg = $('#chat-container').children().last();
    if (lastMsg.find('.bg-nothing-red').length > 0) {
        lastMsg.remove();
        currentAiMessageId = `msg-${Date.now()}`;
        appendMessage('ai', '', currentAiMessageId);
        setGeneratingState(true);
        const model = $('#model-select').val();
        socket.emit('regenerate', {
            session_id: currentSessionId, model: model,
            temperature: config.temperature,
            options: getModelOptions()
        });
    }
}


// --- RENDERING ---
function appendMessage(role, text, domId, dbId = null, imgBase64 = null, pinned = false) {
    const isUser = role === 'user';
    const finalDomId = domId;
    const dataAttr = dbId ? `data-db-id="${dbId}"` : '';
    const pinIndicator = pinned ? `<span class="text-yellow-500 mr-1 inline-block w-3 h-3">${ICONS.star}</span>` : '';
    const tokenBadge = text ? `<span class="text-[9px] text-gray-600 ml-2">~${estimateTokens(text)}t</span>` : '';
    const pinBtn = dbId ? `<button onclick="togglePinMessage(this, '${dbId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-yellow-500" title="Pin message">${ICONS.starOutline}</button>` : '';
    const actionBar = `<div class="action-bar hidden absolute ${isUser ? '-top-8 right-0' : '-top-8 left-0'} bg-[#222] border border-white/20 rounded-lg flex items-center shadow-xl z-10 px-1 py-1 gap-1">
<button onclick="copyMessage('${finalDomId}', this)" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Copy"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>
${isUser ? `<button onclick="startEdit('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Edit"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>` : `<button onclick="triggerRegenerate()" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Regenerate"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg></button>`}
${pinBtn}
<button onclick="toggleMarkdown(this, '${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Show raw Markdown">&lt;/&gt;</button>
<button onclick="exportMessage('${finalDomId}', 'clipboard')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Copy to clipboard"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>
<button onclick="saveToLibraryFromMsg('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Save to Library"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg></button>
<button onclick="forkChat('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Fork conversation"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg></button>
</div>`;
    const imgHtml = imgBase64 ? `<img src="data:image/jpeg;base64,${imgBase64}" class="max-w-[200px] rounded-lg mb-2 border border-white/10 block">` : '';
    const cursor = !isUser && !text ? '<span class="typing-cursor"></span>' : '';
    const html = `<div class="flex gap-3 ${isUser ? 'flex-row-reverse' : ''} fade-in group max-w-3xl mx-auto relative mb-6" ${dataAttr} id="wrapper-${finalDomId}">
<div class="w-8 h-8 rounded-full ${isUser ? 'bg-white' : 'bg-nothing-red'} flex items-center justify-center shrink-0 font-mono font-bold text-[10px] text-black shadow-lg border border-white/20 mt-1 select-none cursor-default">${isUser ? 'U' : 'AI'}</div>
<div class="relative max-w-[85%]">
${actionBar}
<div onclick="toggleActions('${finalDomId}')" class="msg-bubble cursor-pointer ${isUser ? 'bg-white/10' : 'bg-[#151515] border border-white/5'} rounded-2xl ${isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'} px-5 py-3 shadow-sm prose prose-invert break-words">
${imgHtml}
<div class="flex items-center gap-2 mb-1">${pinIndicator}<span class="text-[10px] text-gray-600 font-mono">${timeAgo(new Date().toISOString())}</span>${tokenBadge}</div>
<div id="${finalDomId}" class="prose-content">${cursor}</div>
</div></div></div>`;
    $('#chat-container').append(html);
    if (text) {
        const el = document.getElementById(finalDomId);
        el.innerHTML = marked.parse(text);
        highlightCode(el);
        addCodeCopyButtons(el);
    }
}

function toggleActions(id) {
    const bar = $(`#wrapper-${id}`).find('.action-bar');
    $('.action-bar').not(bar).addClass('hidden');
    bar.toggleClass('hidden');
}


// --- SOCKETS ---
socket.on('message_saved', (data) => {
    if (data.temp_id) {
        const wrapper = $(`#wrapper-${data.temp_id}`);
        const content = document.getElementById(data.temp_id);
        if (wrapper.length) {
            wrapper.attr('data-db-id', data.db_id);
            wrapper.attr('id', `wrapper-msg-${data.db_id}`);
            content.id = `msg-${data.db_id}`;
            wrapper.find('.msg-bubble').attr('onclick', `toggleActions('msg-${data.db_id}')`);
            wrapper.find('button[title="Copy"]').attr('onclick', `copyMessage('msg-${data.db_id}', this)`);
            wrapper.find('button[title="Edit"]').attr('onclick', `startEdit('msg-${data.db_id}')`);
            wrapper.find('button[title="Save to Library"]').attr('onclick', `saveToLibraryFromMsg('msg-${data.db_id}')`);
            wrapper.find('button[title="Fork conversation"]').attr('onclick', `forkChat('msg-${data.db_id}')`);
            wrapper.find('button[title="Pin message"]').attr('onclick', `togglePinMessage(this, '${data.db_id}')`);
        }
    }
});

socket.on('stream_chunk', (data) => {
    const aiDiv = document.getElementById(currentAiMessageId);
    if (aiDiv) {
        let raw = aiDiv.getAttribute('data-raw') || "";
        raw += data.chunk;
        aiDiv.setAttribute('data-raw', raw);
        aiDiv.innerHTML = marked.parse(raw) + '<span class="typing-cursor"></span>';
        highlightCode(aiDiv);
        if (autoScroll) scrollToBottom();
        if (data.tps) {
            const speedEl = $('#speed-meter');
            const maxTxt = data.max_tokens ? ` / ${data.max_tokens}` : '';
            const txt = `${data.tokens}${maxTxt} tok · ${data.tps} t/s`;
            if (!speedEl.length) {
                $(`<div id="speed-meter" class="text-[9px] text-gray-600 font-mono text-center py-1">${txt}</div>`).insertBefore('#chat-container > .flex:last');
            } else {
                speedEl.text(txt);
            }
        }
    }
});

socket.on('stream_done', () => {
    const aiDiv = document.getElementById(currentAiMessageId);
    if (aiDiv) {
        let raw = aiDiv.getAttribute('data-raw');
        aiDiv.innerHTML = marked.parse(raw);
        highlightCode(aiDiv);
        addCodeCopyButtons(aiDiv);
    }
    $('#speed-meter').remove();
    setGeneratingState(false);
});

socket.on('session_created', (data) => { currentSessionId = data.session_id; loadHistoryList(); });


// --- FORK ---
function forkChat(domId) {
    const wrapper = $(`#wrapper-${domId}`);
    const dbId = wrapper.attr('data-db-id');
    if (!currentSessionId || !dbId) return;
    if (!confirm('Fork conversation from this message?')) return;
    $.ajax({
        url: '/api/fork', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ session_id: currentSessionId, msg_id: dbId }),
        success: (res) => { loadSession(res.session_id); },
        error: () => { showToast("Fork failed.", 'error'); }
    });
}


// --- EDITING ---
function startEdit(id) {
    const wrapper = $(`#wrapper-${id}`);
    const dbId = wrapper.attr('data-db-id');
    const contentDiv = $(`#${id}`);
    const rawText = contentDiv.text();
    const editHtml = `<div class="edit-box w-full mt-2 bg-[#111] p-2 rounded border border-white/10 animate-fade-in"><textarea id="edit-area-${dbId}" class="w-full bg-transparent text-white p-2 text-sm focus:outline-none font-mono" rows="3">${rawText}</textarea><div class="flex gap-2 justify-end mt-2"><button onclick="cancelEdit('${id}')" class="px-3 py-1 text-xs text-gray-400 hover:text-white border border-white/10 rounded">Cancel</button><button onclick="submitEdit('${dbId}', '${id}')" class="px-3 py-1 text-xs bg-nothing-red text-white rounded font-bold">Update</button></div></div>`;
    wrapper.find('.msg-bubble').hide();
    wrapper.find('.action-bar').addClass('hidden');
    wrapper.append(editHtml);
}

function cancelEdit(id) {
    const wrapper = $(`#wrapper-${id}`);
    wrapper.find('.edit-box').remove();
    wrapper.find('.msg-bubble').show();
}

function submitEdit(dbId, domId) {
    const newText = $(`#edit-area-${dbId}`).val();
    const wrapper = $(`#wrapper-${domId}`);
    wrapper.find('.edit-box').remove();
    wrapper.find('.msg-bubble').show();
    wrapper.find('.prose-content').text(newText);
    wrapper.nextAll().remove();
    sendMessage(newText, true, dbId);
}


// --- CONFIG & LOADERS ---
function toggleSettings() { $('#settings-modal').toggleClass('hidden'); }

function checkAuth() {
    $.get('/api/auth/me', (data) => {
        if (data.user_id) {
            currentUserId = data.user_id;
            $('#auth-user-info').text(data.username);
            $('#profile-link').removeClass('hidden');
            $('#logout-btn').removeClass('hidden');
            if (data.role === 'admin') $('#admin-btn').removeClass('hidden');

            const initialsEl = $('#profile-initials-mini');
            const imgEl = $('#profile-pic-mini');
            if (data.profile_pic) {
                imgEl.attr('src', data.profile_pic).removeClass('hidden');
                initialsEl.addClass('hidden');
            } else {
                imgEl.addClass('hidden');
                initialsEl.removeClass('hidden');
                const name = data.full_name || data.username;
                const parts = name.trim().split(/\s+/);
                initialsEl.text(parts.length > 1 ? (parts[0][0] + parts[parts.length-1][0]).toUpperCase() : parts[0][0].toUpperCase());
            }
        }
    }).fail(() => {
        window.location.href = '/login';
    });
}

function doLogout() {
    $.ajax({ url: '/api/auth/logout', type: 'POST', success: () => { window.location.href = '/login'; } });
}

function saveSettings() {
    const sys = $('#setting-system').val();
    config.temperature = $('#setting-temp').val();
    $.ajax({
        url: '/api/config', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ system_prompt: sys }),
        success: () => { toggleSettings(); showToast('Settings saved', 'success'); }
    });
    saveProviderConfig();
    $.ajax({
        url: '/api/user/settings', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({
            model: $('#setting-user-model').val(),
            temperature: $('#setting-temp').val(),
        }),
    });
}

function loadUserModelSelect() {
    const sel = $('#setting-user-model');
    const currentVal = sel.val();
    $.get('/api/models', (data) => {
        const models = data.models || data || [];
        sel.empty().append('<option value="">Use provider default</option>');
        if (Array.isArray(models)) {
            models.forEach(m => {
                const name = typeof m === 'string' ? m : (m.name || m.model || '');
                if (name) sel.append('<option value="' + escapeHtml(name) + '">' + escapeHtml(name) + '</option>');
            });
        }
        $.get('/api/user/settings', (us) => {
            if (us.model) sel.val(us.model);
        });
    });
}

function loadSettings() {
    $.get('/api/config', (data) => {
        $('#setting-system').val(data.system_prompt);
        const sel = $('#template-select');
        sel.empty().append('<option value="">Select a template...</option>');
        if (data.templates) {
            Object.entries(data.templates).forEach(([name, content]) => {
                sel.append(`<option value="${escapeHtml(content)}">${escapeHtml(name)}</option>`);
            });
        }
    });
    $('#setting-temp').val(config.temperature);
    $('#temp-display').text(config.temperature);
    const savedAccent = localStorage.getItem('ln-accent') || '#D71921';
    $('#accent-picker').val(savedAccent);
    $('#accent-color-display').text(savedAccent);
    const savedFontSize = localStorage.getItem('ln-font-size') || '14px';
    const fsNum = parseInt(savedFontSize);
    $('#font-size-slider').val(fsNum);
    $('#font-size-display').text(savedFontSize);
    loadProviderConfig();
    loadUserTools();
}

function applyTemplate() {
    const val = $('#template-select').val();
    if (val) $('#setting-system').val(val);
}

function applyAccentColor(color) {
    $('#accent-color-display').text(color);
    document.documentElement.style.setProperty('--accent', color);
    localStorage.setItem('ln-accent', color);
    let styleEl = document.getElementById('ln-accent-override');
    if (!styleEl) {
        styleEl = document.createElement('style');
        styleEl.id = 'ln-accent-override';
        document.head.appendChild(styleEl);
    }
    styleEl.textContent = `
        .bg-nothing-red { background-color: ${color} !important; }
        .text-nothing-red { color: ${color} !important; }
        .border-nothing-red { border-color: ${color} !important; }
        .accent-nothing-red { accent-color: ${color} !important; }
        .hover\\:border-nothing-red\\/50:hover { border-color: ${color}80 !important; }
        .hover\\:border-nothing-red:hover { border-color: ${color} !important; }
        .hover\\:bg-nothing-red\\/30:hover { background-color: ${color}4D !important; }
        .selection\\:bg-nothing-red::selection { background-color: ${color} !important; }
        .ring-nothing-red { --tw-ring-color: ${color} !important; }
        .focus\\:border-nothing-red:focus { border-color: ${color} !important; }
    `;
}

function applyFontSize(size) {
    const px = size + 'px';
    $('#font-size-display').text(px);
    $('body').css('font-size', px);
    localStorage.setItem('ln-font-size', px);
}

function changeAccent() {
    const c = prompt("Accent color (hex, e.g. #D71921):", localStorage.getItem('ln-accent') || '#D71921');
    if (c) applyAccentColor(c);
}

function changeFontSize() {
    const s = prompt('Enter font size (px):', document.body.style.fontSize || '14');
    if (s) { $('body').css('font-size', s); localStorage.setItem('ln-font-size', s); }
}

// --- THEME TOGGLE ---
function toggleTheme() {
    const html = document.documentElement;
    const isDark = html.className !== 'light';
    html.className = isDark ? 'light' : 'dark';
    localStorage.setItem('ln-theme', isDark ? 'light' : 'dark');
    $('#icon-sun, #icon-moon').toggleClass('hidden');
}

function initThemeIcon() {
    const isLight = document.documentElement.className === 'light';
    $('#icon-sun').toggleClass('hidden', !isLight);
    $('#icon-moon').toggleClass('hidden', isLight);
}

// --- SESSION SEARCH (within current chat) ---
function toggleSessionSearch() {
    const overlay = document.getElementById('session-search-overlay');
    if (!overlay) return;
    overlay.classList.toggle('active');
    if (overlay.classList.contains('active')) {
        document.getElementById('session-search-input').focus();
    }
}

function filterSessionMessages() {
    const q = document.getElementById('session-search-input').value.trim().toLowerCase();
    const container = document.getElementById('chat-messages');
    const wrappers = container.querySelectorAll('[id^="wrapper-"]');
    wrappers.forEach(w => {
        const text = w.textContent.toLowerCase();
        if (!q) { w.style.display = ''; return; }
        w.style.display = text.includes(q) ? '' : 'none';
        if (q && text.includes(q)) {
            w.innerHTML = w.innerHTML.replace(/<mark class="search-highlight">(.*?)<\/mark>/g, '$1');
            const idx = text.indexOf(q);
            if (idx >= 0) {
                const original = w.innerHTML;
                const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                w.innerHTML = original.replace(new RegExp(`(${escaped})`, 'gi'), '<mark class="search-highlight">$1</mark>');
            }
        }
    });
}

// --- BRANCH TREE ---
function loadBranchTree(sessionId) {
    if (!sessionId) { $('#branch-tree-panel').addClass('hidden'); return; }
    $.get(`/api/sessions/${sessionId}/branches`, (branches) => {
        const panel = $('#branch-tree-panel');
        if (!branches || branches.length <= 1) { panel.addClass('hidden'); return; }
        panel.removeClass('hidden');
        let html = '<div class="font-mono font-bold text-[10px] text-gray-500 uppercase mb-2">Conversation Tree</div>';
        branches.forEach(b => {
            const active = b.id === sessionId ? 'active' : '';
            const indent = b.depth > 0 ? 'style="padding-left:' + (32 + b.depth * 16) + 'px"' : '';
            const label = b.title ? b.title.substring(0, 20) : 'Chat';
            html += `<div class="branch-node ${active}" ${indent} onclick="switchBranch('${b.id}')"><span class="branch-label">${escapeHtml(label)}</span></div>`;
        });
        panel.html(html);
    }).fail(() => { $('#branch-tree-panel').addClass('hidden'); });
}

function switchBranch(sessionId) {
    loadSession(sessionId);
    $('#branch-tree-panel').addClass('hidden');
}

// --- MARKDOWN TOGGLE ---
function toggleMarkdown(btn, msgId) {
    const el = document.getElementById(msgId);
    if (!el) return;
    const isRaw = el.dataset.mode === 'raw';
    if (isRaw) {
        el.innerHTML = marked.parse(el.dataset.original || el.textContent) + '<span class="typing-cursor"></span>';
        el.dataset.mode = 'rendered';
        btn.innerHTML = '&lt;/&gt;';
        btn.title = 'Show raw Markdown';
    } else {
        el.dataset.original = el.innerHTML;
        el.textContent = el.textContent.replace(/<span[^>]*>.*?<\/span>/g, '').trim();
        el.dataset.mode = 'raw';
        btn.innerHTML = 'R';
        btn.title = 'Render Markdown';
    }
    highlightCode(el);
}

// --- EXPORT SINGLE MESSAGE ---
function exportMessage(msgId, format) {
    const dbId = $(`#wrapper-${msgId}`).data('db-id') || $(`#${msgId}`).closest('[data-db-id]').data('db-id');
    if (!dbId) { showToast('Message not saved yet', 'warning'); return; }
    if (format === 'clipboard') {
        const text = document.getElementById(msgId).innerText;
        navigator.clipboard.writeText(text).then(() => showToast('Copied to clipboard', 'success'));
        return;
    }
    window.open(`/api/messages/${dbId}/export?format=${format}`, '_blank');
}

// --- PROVIDER CONFIG ---
function loadProviderConfig() {
    $.get('/api/provider/config', (data) => {
        $('#setting-provider').val(data.provider || 'ollama');
        $('#setting-api-key').val(data.api_key || '');
        $('#setting-ollama-url').val(data.ollama_url || 'http://localhost:11434');
        onProviderChange();
    });
    loadUserModelSelect();
}

function onProviderChange() {
    const p = $('#setting-provider').val();
    if (p === 'ollama') {
        $('#provider-api-key-group').addClass('hidden');
        $('#setting-ollama-url').closest('div').removeClass('hidden');
    } else {
        $('#provider-api-key-group').removeClass('hidden');
        $('#setting-ollama-url').closest('div').addClass('hidden');
    }
}

function saveProviderConfig() {
    const prov = $('#setting-provider').val();
    const data = {
        provider: prov,
        api_key: $('#setting-api-key').val(),
        ollama_url: prov === 'ollama' ? $('#setting-ollama-url').val() : '',
    };
    $.ajax({
        url: '/api/provider/config', type: 'POST', contentType: 'application/json',
        data: JSON.stringify(data),
        success: () => { showToast('Provider config saved', 'success'); loadModels(); },
        error: () => { showToast('Failed to save provider config', 'error'); }
    });
}

function deleteAccount() {
    const pw = document.getElementById('delete-account-pw').value;
    if (!pw) { showToast('Enter your password to confirm', 'error'); return; }
    if (!confirm('Are you sure? This permanently deletes your account and all data.')) return;
    $.ajax({
        url: '/api/account/delete', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ password: pw }),
        success: () => { showToast('Account deleted'); setTimeout(() => window.location.href = '/login', 1500); },
        error: (x) => { const r = x.responseJSON; showToast(r && r.error ? r.error : 'Delete failed', 'error'); }
    });
}

function loadUserTools() {
    $.get('/api/tools', (tools) => {
        const el = document.getElementById('user-tools-list');
        if (!el) return;
        if (!tools || !tools.length) { el.innerHTML = '<div class="text-[10px] text-gray-600 font-mono">No custom tools configured.</div>'; return; }
        el.innerHTML = tools.map(t => {
            let name = '';
            try { const d = JSON.parse(t.definition); name = d.function ? d.function.name : t.name; } catch(e) { name = t.name; }
            return '<div class="flex items-center justify-between bg-[#151515] rounded px-2 py-1.5 border border-white/5">' +
                '<div><span class="text-xs text-gray-300 font-mono">' + escapeHtml(name) + '</span>' +
                '<span class="text-[10px] text-gray-600 font-mono ml-2">' + escapeHtml(t.description || '') + '</span></div>' +
                '<button onclick="deleteUserTool(\'' + t.id + '\')" class="text-red-500 hover:text-red-400 text-[10px] font-mono underline">Delete</button></div>';
        }).join('');
    });
}

function saveUserTool() {
    const name = document.getElementById('new-tool-name').value.trim();
    const desc = document.getElementById('new-tool-desc').value.trim();
    let def = document.getElementById('new-tool-def').value.trim();
    if (!name || !def) { showToast('Tool name and definition required', 'error'); return; }
    try { def = JSON.parse(def); } catch(e) { showToast('Invalid JSON definition', 'error'); return; }
    $.ajax({
        url: '/api/tools', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ name, description: desc, definition: def }),
        success: () => { showToast('Tool created', 'success'); document.getElementById('add-tool-form').classList.add('hidden'); document.getElementById('new-tool-name').value = ''; document.getElementById('new-tool-desc').value = ''; document.getElementById('new-tool-def').value = ''; loadUserTools(); },
        error: (x) => { const r = x.responseJSON; showToast(r && r.error ? r.error : 'Failed', 'error'); }
    });
}

function deleteUserTool(toolId) {
    if (!confirm('Delete this tool?')) return;
    $.ajax({
        url: '/api/tools/' + toolId, type: 'DELETE',
        success: () => { showToast('Tool deleted', 'success'); loadUserTools(); },
        error: () => { showToast('Delete failed', 'error'); }
    });
}

function showAddToolForm() { document.getElementById('add-tool-form').classList.remove('hidden'); }

function exportTheme() {
    const theme = {
        accent: localStorage.getItem('ln-accent') || '#D71921',
        fontSize: localStorage.getItem('ln-font-size') || '14px'
    };
    const blob = new Blob([JSON.stringify(theme, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'localneural-theme.json'; a.click();
    URL.revokeObjectURL(url);
    showToast('Theme exported', 'success');
}

function importTheme() {
    const input = document.createElement('input');
    input.type = 'file'; input.accept = '.json';
    input.onchange = function () {
        if (!input.files[0]) return;
        const reader = new FileReader();
        reader.onload = function (e) {
            try {
                const theme = JSON.parse(e.target.result);
                if (theme.accent) applyAccentColor(theme.accent);
                if (theme.fontSize) applyFontSize(parseInt(theme.fontSize));
                showToast('Theme imported', 'success');
            } catch (err) { showToast('Invalid theme file', 'error'); }
        };
        reader.readAsText(input.files[0]);
    };
    input.click();
}

function loadSession(id) {
    currentSessionId = id;
    $.get(`/api/chat/${id}`, (data) => {
        $('#chat-container').empty();
        $('#welcome-msg').addClass('hidden');
        if (data.model) $('#model-select').val(data.model);
        if (data.project_id) { activeProjectId = data.project_id; $('#active-project-name').text(`PROJECT MODE`).removeClass('hidden'); }
        else { activeProjectId = null; $('#active-project-name').addClass('hidden'); }
        if (data.system_prompt) { config.custom_session_prompt = data.system_prompt; }
        else { config.custom_session_prompt = null; }
        data.messages.forEach(x => {
            let i = null;
            if (x.images) { try { i = JSON.parse(x.images)[0]; } catch (e) { } }
            const isPinned = x.pinned === 1 || x.pinned === '1';
            appendMessage(x.role === 'user' ? 'user' : 'ai', x.content, `msg-${x.id}`, x.id, i, isPinned);
            if (x.timestamp) {
                const bubble = $(`#wrapper-msg-${x.id}`).find('.text-gray-600.font-mono').first();
                if (bubble.length) bubble.text(timeAgo(x.timestamp));
            }
        });
        loadBranchTree(id);
        if (window.innerWidth < 768) toggleSidebar();
        scrollToBottom();
    });
}


// --- UTILS ---
function toggleLibrary() { $('#library-modal').toggleClass('hidden'); }

function loadLibrary() {
    $.get('/api/prompts', (d) => {
        $('#library-list').empty();
        d.forEach(p => $('#library-list').append(`<div class="bg-[#151515] p-3 rounded border border-white/5 hover:border-white/20 flex justify-between items-start group"><div onclick="usePrompt('${escapeHtml(p.content)}')" class="cursor-pointer flex-1"><div class="font-bold text-sm text-gray-300">${escapeHtml(p.title)}</div><div class="text-xs text-gray-500 line-clamp-2 mt-1 font-mono">${escapeHtml(p.content)}</div></div><button onclick="deletePrompt(${p.id})" class="text-gray-600 hover:text-red-500 px-2">×</button></div>`));
    });
}

function savePrompt() {
    const t = $('#new-prompt-title').val();
    const c = $('#new-prompt-content').val();
    if (t && c) $.ajax({ url: '/api/prompts', type: 'POST', contentType: 'application/json', data: JSON.stringify({ title: t, content: c }), success: () => { loadLibrary(); $('#new-prompt-title').val(''); $('#new-prompt-content').val(''); showToast('Prompt saved', 'success'); } });
}

function deletePrompt(id) { $.ajax({ url: `/api/prompts/${id}`, type: 'DELETE', success: loadLibrary }); }

function usePrompt(text) { $('#user-input').val(text); toggleLibrary(); $('#user-input').focus(); }

function saveToLibraryFromMsg(id) {
    const text = document.getElementById(id).innerText;
    const title = prompt("Name:", text.substring(0, 20));
    if (title) $.ajax({ url: '/api/prompts', type: 'POST', contentType: 'application/json', data: JSON.stringify({ title: title, content: text }), success: () => { showToast("Saved", 'success'); loadLibrary(); } });
}

function togglePinMessage(btn, dbId) {
    $.ajax({
        url: `/api/messages/${dbId}/pin`, type: 'POST',
        success: (res) => {
            if (res.pinned) { $(btn).addClass('text-yellow-500').removeClass('text-gray-400'); showToast('Message pinned', 'info'); }
            else { $(btn).removeClass('text-yellow-500').addClass('text-gray-400'); showToast('Message unpinned', 'info'); }
            loadSession(currentSessionId);
        },
        error: () => { showToast('Failed to toggle pin', 'error'); }
    });
}

function copyMessage(id, btn) {
    const text = document.getElementById(id).innerText;
    if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(() => showCopied(btn)); } else { const ta = document.createElement("textarea"); ta.value = text; document.body.appendChild(ta); ta.select(); try { document.execCommand('copy'); showCopied(btn); } catch (e) { } document.body.removeChild(ta); }
}

function showCopied(btn) { const h = $(btn).html(); $(btn).html('✓'); setTimeout(() => $(btn).html(h), 1500); }

function highlightCode(el) { el.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b)); }

function addCodeCopyButtons(el) {
    $(el).find('pre').each(function () {
        if ($(this).find('.code-header').length === 0) {
            const w = $('<div class="code-wrapper"></div>');
            $(this).wrap(w);
            const h = $(`<div class="code-header"><span>code</span><span class="cursor-pointer hover:text-white transition copy-btn">COPY</span></div>`);
            h.find('.copy-btn').click(function () {
                const c = $(this).closest('.code-wrapper').find('code').text();
                const ta = document.createElement("textarea"); ta.value = c; document.body.appendChild(ta); ta.select();
                try { document.execCommand('copy'); showCopied(this); } catch (e) { }
                document.body.removeChild(ta);
            });
            $(this).closest('.code-wrapper').prepend(h);
        }
    });
}

function handleImageSelect(input) { if (input.files && input.files[0]) handleFileProcess(input.files[0]); }

function handleFileProcess(file) {
    const r = new FileReader();
    r.readAsDataURL(file);
    r.onload = (e) => {
        const i = new Image(); i.src = e.target.result;
        i.onload = () => {
            const c = document.createElement('canvas');
            const s = 800 / i.width; c.width = 800; c.height = i.height * s;
            const x = c.getContext('2d'); x.drawImage(i, 0, 0, c.width, c.height);
            const d = c.toDataURL('image/jpeg', 0.7);
            attachedImageBase64 = d.split(',')[1];
            $('#preview-src').attr('src', d); $('#img-preview').removeClass('hidden');
        }
    }
}

function handlePaste(e) {
    const items = (e.clipboardData || e.originalEvent.clipboardData).items;
    for (let i in items) { if (items[i].kind === 'file' && items[i].type.startsWith('image/')) { handleFileProcess(items[i].getAsFile()); e.preventDefault(); } }
}

function clearImage() { attachedImageBase64 = null; $('#img-upload').val(''); $('#img-preview').addClass('hidden'); }

// --- FILE ATTACHMENT (ad-hoc Q&A) ---
function handleChatFileDrop(file) {
    if (file.type.startsWith('image/')) { handleFileProcess(file); return; }
    uploadChatFile(file);
}

function handleFileSelect(input) {
    if (input.files && input.files[0]) uploadChatFile(input.files[0]);
}

function uploadChatFile(file) {
    const validExts = ['.pdf', '.docx', '.csv', '.json', '.txt', '.md', '.py', '.js', '.ts', '.html', '.css', '.xml', '.yaml', '.yml', '.log'];
    const ext = '.' + file.name.split('.').pop().toLowerCase();
    if (!validExts.includes(ext)) { showToast('Unsupported file type: ' + ext, 'error'); return; }
    const fd = new FormData();
    fd.append('file', file);
    showToast('Uploading ' + file.name + '...', 'info');
    $.ajax({
        url: '/api/chat/upload', type: 'POST', data: fd, contentType: false, processData: false,
        success: (res) => {
            if (res.content) {
                attachedFile = { name: res.filename, content: res.content };
                showToast(`Attached: ${res.filename} (${(res.size / 1024).toFixed(1)} KB)`, 'success');
                $('#file-attach-badge').removeClass('hidden').find('.file-name').text(res.filename);
            }
        },
        error: (e) => { showToast('Upload failed: ' + (e.responseJSON?.error || e.statusText), 'error'); }
    });
}

function clearAttachedFile() {
    attachedFile = null;
    $('#file-attach-badge').addClass('hidden');
    $('#file-upload').val('');
}

function toggleAutoScroll() { autoScroll = !autoScroll; $('#autoscroll-btn').toggleClass('hidden', autoScroll); if (autoScroll) scrollToBottom(); }

function checkScroll() {
    const el = document.getElementById('chat-container');
    if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) { autoScroll = true; $('#autoscroll-btn').addClass('hidden'); }
    else { autoScroll = false; $('#autoscroll-btn').removeClass('hidden'); }
}

function setGeneratingState(gen) {
    isGenerating = gen; const b = $('#action-btn');
    if (gen) { $('#icon-send').addClass('hidden'); $('#icon-stop').removeClass('hidden'); b.addClass('bg-nothing-red text-white').removeClass('bg-white text-black'); }
    else { $('#icon-send').removeClass('hidden'); $('#icon-stop').addClass('hidden'); b.removeClass('bg-nothing-red text-white').addClass('bg-white text-black'); }
}

function toggleSidebar() { $('#sidebar').toggleClass('-translate-x-full'); $('#mobile-overlay').toggleClass('hidden'); }

function filterHistory() {
    const val = $(this).val().toLowerCase();
    $('.history-item').each(function () { $(this).toggle($(this).text().toLowerCase().indexOf(val) > -1); });
}

function renameChat(e, id, old) {
    e.stopPropagation();
    const span = $(e.currentTarget);
    const input = $(`<input type="text" value="${escapeHtml(old)}" class="bg-transparent text-xs text-white font-mono w-full focus:outline-none border-b border-nothing-red">`);
    span.replaceWith(input);
    input.focus();
    input.select();
    input.on('blur', function () {
        const n = $(this).val().trim();
        if (n && n !== old) $.ajax({ url: '/api/rename', type: 'POST', contentType: 'application/json', data: JSON.stringify({ id, title: n }), success: loadHistoryList });
        else loadHistoryList();
    });
    input.on('keydown', function (e) {
        if (e.key === 'Enter') $(this).blur();
        if (e.key === 'Escape') { loadHistoryList(); }
    });
}

function toggleSelect(e, id) {
    e.stopPropagation();
    if (selectedIds.has(id)) selectedIds.delete(id); else selectedIds.add(id);
    $(`#history-check-${id}`).prop('checked', selectedIds.has(id));
    $(`#wrapper-session-${id}`).toggleClass('border-nothing-red', selectedIds.has(id));
    $('#bulk-delete-btn').toggle(selectedIds.size > 0);
}

function toggleSelectAll() {
    const all = $('.history-item-checkbox');
    const allChecked = all.length === all.filter(':checked').length;
    all.prop('checked', !allChecked);
    $('.history-item').each(function () {
        const id = $(this).data('sid');
        if (!allChecked) { selectedIds.add(id); $(this).addClass('border-nothing-red'); }
        else { selectedIds.delete(id); $(this).removeClass('border-nothing-red'); }
    });
    $('#bulk-delete-btn').toggle(selectedIds.size > 0);
}

function bulkDeleteSelected() {
    if (selectedIds.size === 0) return;
    if (!confirm(`Delete ${selectedIds.size} conversation(s)?`)) return;
    $.ajax({
        url: '/api/bulk-delete', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ ids: Array.from(selectedIds) }),
        success: () => { selectedIds.clear(); $('#bulk-delete-btn').hide(); loadHistoryList(); showToast('Deleted', 'success'); }
    });
}

function deleteSession(e, id) {
    e.stopPropagation();
    if (confirm('Delete trace?')) $.ajax({ url: `/api/delete/${id}`, type: 'DELETE', success: loadHistoryList });
}

function archiveSession(e, id, archived = true) {
    e.stopPropagation();
    $.ajax({ url: `/api/archive/${id}`, type: 'POST', contentType: 'application/json', data: JSON.stringify({ archived }), success: loadHistoryList });
}

function pinSession(e, id) {
    e.stopPropagation();
    $.ajax({ url: `/api/pin/${id}`, type: 'POST', contentType: 'application/json', data: JSON.stringify({ pinned: true }), success: loadHistoryList });
}

function unpinSession(e, id) {
    e.stopPropagation();
    $.ajax({ url: `/api/pin/${id}`, type: 'POST', contentType: 'application/json', data: JSON.stringify({ pinned: false }), success: loadHistoryList });
}

function newChat(keepProject = false) {
    currentSessionId = null;
    config.custom_session_prompt = null;
    if (!keepProject) { activeProjectId = null; $('#active-project-name').addClass('hidden'); }
    if (attachedFile) clearAttachedFile();
    if (attachedImageBase64) clearImage();
    $('#chat-container').empty();
    $('#welcome-msg').removeClass('hidden');
    if (window.innerWidth < 768) toggleSidebar();
}

function scrollToBottom() { const c = document.getElementById('chat-container'); c.scrollTop = c.scrollHeight; }

function escapeHtml(t) { return t ? t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") : ''; }

let activeTagFilter = null;

function loadHistoryList() {
    $.get("/api/history", (s) => {
        const l = $("#history-list"); l.empty();
        // Filter by active tag
        if (activeTagFilter) {
            s = s.filter(x => x.tags && x.tags.includes(activeTagFilter));
        }
        let currentGroup = null;
        s.forEach(x => {
            if (x.group_id && x.group_id !== currentGroup) { currentGroup = x.group_id; }
            const projLabel = x.project_title ? `<span class="ml-2 text-[9px] bg-nothing-red px-1 rounded text-white opacity-70">${escapeHtml(x.project_title)}</span>` : '';
            const tokenBadge = x.total_tokens ? `<span class="text-[9px] text-gray-600 ml-1">${x.total_tokens}t</span>` : '';
            const pinned = x.pinned === '1';
            const pinBtn = pinned
                ? `<button onclick="unpinSession(event,'${x.id}')" class="text-yellow-500 hover:text-white p-1" title="Unpin">${ICONS.pin}</button>`
                : `<button onclick="pinSession(event,'${x.id}')" class="text-gray-500 hover:text-yellow-500 p-1" title="Pin">${ICONS.pin}</button>`;
            const archiveBtn = x.archived
                ? `<button onclick="archiveSession(event,'${x.id}',false)" class="text-gray-500 hover:text-white p-1" title="Unarchive">${ICONS.unarchive}</button>`
                : `<button onclick="archiveSession(event,'${x.id}',true)" class="text-gray-500 hover:text-yellow-500 p-1" title="Archive">${ICONS.archive}</button>`;
            const tagsHtml = x.tags && x.tags.length
                ? `<div class="flex flex-wrap gap-1 mt-1">${x.tags.map(t => `<span class="text-[9px] bg-white/10 text-gray-400 rounded px-1.5 py-0.5 cursor-pointer hover:bg-nothing-red/30 hover:text-white" onclick="event.stopPropagation();setTagFilter('${t}')">#${t}</span>`).join('')}</div>`
                : '';
            l.append(`<div class="history-item group relative flex items-center justify-between p-2 hover:bg-white/5 rounded-lg cursor-pointer transition border border-transparent hover:border-white/5 mx-1 my-0.5 ${x.archived ? 'opacity-50' : ''} ${pinned ? 'border-l-2 border-yellow-600' : ''}" onclick="loadSession('${x.id}')" data-sid="${x.id}" id="wrapper-session-${x.id}">
<input type="checkbox" class="history-item-checkbox hidden group-hover:inline-block ml-1 accent-nothing-red shrink-0" id="history-check-${x.id}" onclick="toggleSelect(event,'${x.id}')">
<div class="flex-1 min-w-0">
<div class="title-text truncate text-xs text-gray-400 font-mono flex items-center gap-1" ondblclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')">${pinned ? `<span class="text-yellow-500 w-3 h-3 inline-block">${ICONS.pin}</span>` : ''}<span class="truncate">${escapeHtml(x.title)}</span>${projLabel}${tokenBadge}</div>
${tagsHtml}
</div>
<div class="flex gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0">
${pinBtn}${archiveBtn}
<button onclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')" class="text-gray-500 hover:text-white p-1 text-xs" title="Rename">${ICONS.pencil}</button>
<button onclick="deleteSession(event,'${x.id}')" class="text-gray-500 hover:text-red-500 p-1" title="Delete">${ICONS.trash}</button>
</div></div>`);
        });
    });
}

function setTagFilter(tag) {
    if (activeTagFilter === tag) activeTagFilter = null;
    else activeTagFilter = tag;
    loadHistoryList();
    loadAllTags();
}

function loadAllTags() {
    $.get('/api/tags', (tags) => {
        const el = $('#tag-filters');
        el.empty();
        if (activeTagFilter) {
            el.append(`<button onclick="setTagFilter(null)" class="text-[10px] bg-nothing-red text-white rounded px-2 py-0.5 font-mono flex items-center gap-1">${ICONS.close} clear</button>`);
        }
        tags.forEach(t => {
            const active = activeTagFilter === t ? 'bg-nothing-red/30 text-white border-nothing-red' : 'bg-white/5 text-gray-500 hover:text-white';
            el.append(`<button onclick="setTagFilter('${t}')" class="text-[10px] ${active} rounded px-2 py-0.5 font-mono border border-white/10 transition">#${t}</button>`);
        });
    });
}

function addTagToSession() {
    const tag = prompt("Add tag (lowercase, spaces become hyphens):");
    if (!tag || !currentSessionId) return;
    $.ajax({
        url: `/api/sessions/${currentSessionId}/tags`, type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ tag }),
        success: () => { loadHistoryList(); loadAllTags(); showToast('Tag added', 'success'); },
        error: () => { showToast('Failed to add tag', 'error'); }
    });
}

function loadModels() {
    $.get("/api/models", (d) => {
        const s = $("#model-select"); s.empty();
        if (d.models) d.models.forEach(m => s.append(`<option value="${m.name}">${m.name}</option>`));
        else s.append(`<option>Ollama Down</option>`);
    });
}

function exportChat(f) {
    if (!currentSessionId) { showToast("Open chat first.", 'warning'); return; }
    if (f === 'html') { window.open(`/api/export/${currentSessionId}?format=html`, '_blank'); }
    else { window.location.href = `/api/export/${currentSessionId}?format=${f}`; }
}

function toggleSessionSettings() {
    const p = prompt("System Prompt for THIS chat:", config.custom_session_prompt || "Default");
    if (p !== null) {
        if (currentSessionId) { $.ajax({ url: `/api/session/${currentSessionId}/config`, type: 'POST', contentType: 'application/json', data: JSON.stringify({ system_prompt: p }), success: () => showToast("Updated session.", 'success') }); }
        else { config.custom_session_prompt = p; showToast("Applied to next new chat.", 'info'); }
    }
}

function summarizeChat() {
    if (!currentSessionId) { showToast("Open a chat first.", 'warning'); return; }
    if (isGenerating) { showToast("Wait for generation to finish.", 'warning'); return; }
    showToast("Summarizing...", 'info');
    const model = $('#model-select').val();
    currentAiMessageId = `msg-${Date.now()}`;
    appendMessage('ai', '', currentAiMessageId);
    setGeneratingState(true);
    $.ajax({
        url: `/api/summarize/${currentSessionId}`, type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ model }),
        success: (res) => {
            if (res.summary) {
                const el = document.getElementById(currentAiMessageId);
                if (el) {
                    el.innerHTML = '<strong class="flex items-center gap-1">' + ICONS.clipboard + ' Chat Summary</strong>\n\n' + marked.parse(res.summary);
                    highlightCode(el);
                    addCodeCopyButtons(el);
                }
                showToast('Summary generated', 'success');
            }
        },
        error: (e) => { showToast('Summarization failed: ' + (e.responseJSON?.error || e.statusText), 'error'); },
        complete: () => { setGeneratingState(false); $('#speed-meter').remove(); }
    });
}

// --- DB BACKUP ---
function exportDB() {
    window.open('/api/db/export', '_blank');
    showToast('Database downloaded', 'success');
}

function importDB() {
    const input = document.createElement('input');
    input.type = 'file';
    input.accept = '.db';
    input.onchange = function () {
        if (!input.files[0]) return;
        const fd = new FormData();
        fd.append('file', input.files[0]);
        $.ajax({
            url: '/api/db/import', type: 'POST', data: fd, contentType: false, processData: false,
            success: () => { showToast('Database restored. Reloading...', 'success'); setTimeout(() => location.reload(), 1000); },
            error: () => { showToast('Import failed', 'error'); }
        });
    };
    input.click();
}

// --- AUDIO ---
let isRecording = false;

function toggleRecording() {
    if (isRecording) {
        if (mediaRecorder && mediaRecorder.state === 'recording') {
            mediaRecorder.stop();
        }
        return;
    }
    isRecording = true;
    audioChunks = [];
    $('#record-btn').addClass('text-red-500');
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            isRecording = false;
            $('#record-btn').removeClass('text-red-500');
            stream.getTracks().forEach(t => t.stop());
            mediaRecorder = null;
            if (audioChunks.length === 0) return;
            const blob = new Blob(audioChunks, { type: 'audio/webm' });
            const fd = new FormData();
            fd.append('audio', blob, 'recording.webm');
            showToast('Transcribing...', 'info');
            $.ajax({
                url: '/api/audio/transcribe', type: 'POST', data: fd, contentType: false, processData: false,
                success: (res) => {
                    if (res.text) {
                        const inp = $('#user-input');
                        const existing = inp.val();
                        inp.val(existing ? existing + ' ' + res.text : res.text);
                        inp.focus();
                        showToast('Transcription complete', 'success');
                    }
                },
                error: () => { showToast('Transcription failed. Is whisper model installed? Pull it: ollama pull whisper', 'error'); }
            });
        };
        mediaRecorder.start();
    }).catch(() => {
        isRecording = false;
        $('#record-btn').removeClass('text-red-500');
        showToast('Microphone access denied', 'error');
    });
}

// --- STATS ---
function loadStats() {
    const display = $('#stats-display');
    display.removeClass('hidden').html('Loading...');
    $.get('/api/stats', (data) => {
        const modelHtml = data.model_counts.map(m => `${escapeHtml(m.model)}: ${m.c}`).join('<br>');
        display.html(`
<div><span class="text-gray-400">Sessions:</span> ${data.active_sessions} active, ${data.archived_sessions} archived</div>
<div><span class="text-gray-400">Messages:</span> ${data.total_messages}</div>
<div><span class="text-gray-400">Est. Tokens:</span> ${(data.total_est_tokens / 1000).toFixed(1)}K</div>
<div><span class="text-gray-400">Models:</span><br>${modelHtml}</div>
        `);
    }).fail(() => { display.html('<span class="text-red-500">Failed to load stats</span>'); });
}


// --- COMPARE ---
function openCompare() {
    const selected = [...selectedIds];
    if (selected.length !== 2) {
        showToast('Select exactly 2 conversations using checkboxes', 'warning');
        return;
    }
    const [idA, idB] = selected;
    $('#compare-heading').text('Loading...');
    $('#compare-col-a').empty().html('<div class="text-gray-500 text-xs text-center p-8">Loading...</div>');
    $('#compare-col-b').empty().html('<div class="text-gray-500 text-xs text-center p-8">Loading...</div>');
    $('#compare-modal').removeClass('hidden');
    $.when(
        $.get(`/api/chat/${idA}`),
        $.get(`/api/chat/${idB}`)
    ).done((dataA, dataB) => {
        const a = dataA[0], b = dataB[0];
        $('#compare-heading').text(`Comparing: "${a.title || 'Chat A'}" vs "${b.title || 'Chat B'}"`);
        renderCompareCol('#compare-col-a', a, 'A');
        renderCompareCol('#compare-col-b', b, 'B');
    }).fail(() => {
        showToast('Failed to load sessions', 'error');
        toggleCompareModal();
    });
}

function toggleCompareModal() {
    $('#compare-modal').addClass('hidden');
}

function renderCompareCol(selector, data, label) {
    const el = $(selector).empty();
    const modelLabel = data.model ? `<span class="text-[10px] text-nothing-red font-mono">${escapeHtml(data.model)}</span>` : '';
    el.append(`<div class="text-xs text-gray-500 font-mono mb-4 border-b border-white/10 pb-2">Session ${label} ${modelLabel}</div>`);
    if (!data.messages || !data.messages.length) {
        el.append('<div class="text-gray-500 text-xs text-center p-8">No messages</div>');
        return;
    }
    data.messages.forEach(m => {
        const role = m.role === 'user' ? 'U' : 'AI';
        const roleColor = m.role === 'user' ? 'bg-white text-black' : 'bg-nothing-red text-white';
        const content = m.content || '(empty)';
        el.append(`<div class="flex gap-2 ${m.role === 'user' ? 'flex-row-reverse' : ''} mb-4"><div class="w-6 h-6 rounded-full ${roleColor} flex items-center justify-center text-[8px] font-bold shrink-0 mt-0.5">${role}</div><div class="bg-[#151515] rounded-lg px-3 py-2 text-xs text-gray-300 max-w-[85%]">${escapeHtml(content.substring(0, 1000))}</div></div>`);
    });
}


// --- HEALTH DASHBOARD ---
function healthCheck() {
    const display = $('#health-display');
    display.removeClass('hidden').text('Checking...');
    $.get('/api/health', (data) => {
        const status = data.status === 'ok' ? 'All systems online' : 'Degraded';
        const ollama = data.ollama ? '<span class="text-green-500">● Running</span>' : '<span class="text-red-500">● Down</span>';
        const size = data.db_size ? (data.db_size / 1024).toFixed(1) + ' KB' : 'Unknown';
        display.html(`Ollama: ${ollama}<br>DB Size: ${size}<br>Status: ${status}`);
        showToast(`Health: ${status}`, data.ollama ? 'success' : 'warning');
    }).fail(() => { display.html('<span class="text-red-500">Health check failed</span>'); showToast('Health check failed', 'error'); });
}
