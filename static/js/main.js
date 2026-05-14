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
let config = { temperature: 0.7 };

$(document).ready(function () {
    loadModels();
    loadHistoryList();
    loadSettings();
    loadLibrary();
    loadProjects();
    loadGroups();

    $('#chat-form').on('submit', handleFormSubmit);
    $('#project-form').on('submit', handleProjectSubmit);

    $('#user-input').on('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); handleFormSubmit(e); }
    });

    document.getElementById('user-input').addEventListener('paste', handlePaste);
    const dz = document.getElementById('user-input');
    dz.addEventListener('dragover', (e) => { e.preventDefault(); $(dz).addClass('border-nothing-red') });
    dz.addEventListener('dragleave', (e) => { e.preventDefault(); $(dz).removeClass('border-nothing-red') });
    dz.addEventListener('drop', (e) => { e.preventDefault(); $(dz).removeClass('border-nothing-red'); if (e.dataTransfer.files[0]) handleFileProcess(e.dataTransfer.files[0]); });

    $('#history-search').on('keyup', filterHistory);
    $('#bulk-delete-btn').on('click', bulkDeleteSelected);
    $('#select-all-btn').on('click', toggleSelectAll);
    socket.on('title_updated', () => loadHistoryList());

    $(document).on('click', function (e) {
        if (!$(e.target).closest('.msg-bubble, .action-bar').length) {
            $('.action-bar').addClass('hidden');
        }
    });

    $('#search-input').on('keyup', function () {
        const q = $(this).val().trim();
        if (q.length < 2) { $('#search-results').empty(); return; }
        $.get(`/api/search?q=${encodeURIComponent(q)}`, (data) => {
            const el = $('#search-results'); el.empty();
            if (!data.length) { el.append('<div class="text-gray-500 text-xs p-4 text-center">No results</div>'); return; }
            data.forEach(m => {
                el.append(`<div class="bg-[#151515] p-3 rounded border border-white/5 hover:border-white/20 cursor-pointer" onclick="loadSession('${m.session_id}');toggleSearchModal();"><div class="text-[10px] text-gray-500 font-mono mb-1">${escapeHtml(m.session_title)} · ${m.role.toUpperCase()} · ${timeAgo(m.timestamp)}</div><div class="text-xs text-gray-300 line-clamp-2">${escapeHtml(m.content.substring(0, 200))}</div></div>`);
            });
        });
    });

    // Keyboard shortcuts
    $(document).on('keydown', function (e) {
        if (e.ctrlKey && e.key === 'k') { e.preventDefault(); toggleSearchModal(); }
        if (e.ctrlKey && e.key === 'n') { e.preventDefault(); newChat(); }
        if (e.ctrlKey && e.key === 'l') { e.preventDefault(); toggleLibrary(); }
        if (e.ctrlKey && e.shiftKey && e.key === 'E') { e.preventDefault(); exportChat('md'); }
    });

    // Theme restoration
    const savedAccent = localStorage.getItem('ln-accent');
    const savedFontSize = localStorage.getItem('ln-font-size');
    if (savedAccent) applyAccentColor(savedAccent);
    if (savedFontSize) $('body').css('font-size', savedFontSize);

    // Audio recording
    if (navigator.mediaDevices) {
        $('#record-btn').on('mousedown', startRecording);
        $('#record-btn').on('mouseup mouseleave', stopRecording);
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
    if (!$('#search-modal').hasClass('hidden')) { $('#search-input').val('').focus(); $('#search-results').empty(); }
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
    const prompt = overridePrompt || $input.val().trim();
    const model = $('#model-select').val();
    if ((!prompt && !attachedImageBase64)) return;
    if (!model) { showToast("Select a model first.", 'warning'); return; }
    $('#welcome-msg').addClass('hidden');
    let tempId = `temp-${Date.now()}`;
    const imgToSend = attachedImageBase64;
    if (!isEdit) {
        $input.val('').css('height', 'auto');
        $input.focus();
        appendMessage('user', prompt, tempId, null, imgToSend);
        if (attachedImageBase64) clearImage();
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
        images: imgToSend ? [imgToSend] : []
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
function appendMessage(role, text, domId, dbId = null, imgBase64 = null) {
    const isUser = role === 'user';
    const finalDomId = domId;
    const dataAttr = dbId ? `data-db-id="${dbId}"` : '';
    const tokenBadge = text ? `<span class="text-[9px] text-gray-600 ml-2">~${estimateTokens(text)}t</span>` : '';
    const actionBar = `<div class="action-bar hidden absolute ${isUser ? '-top-8 right-0' : '-top-8 left-0'} bg-[#222] border border-white/20 rounded-lg flex items-center shadow-xl z-10 px-1 py-1 gap-1">
<button onclick="copyMessage('${finalDomId}', this)" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Copy"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>
${isUser ? `<button onclick="startEdit('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Edit"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>` : `<button onclick="triggerRegenerate()" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Regenerate"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg></button>`}
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
<div class="flex items-center gap-2 mb-1"><span class="text-[10px] text-gray-600 font-mono">${timeAgo(new Date().toISOString())}</span>${tokenBadge}</div>
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
        // Speed meter
        if (data.tps) {
            const speedEl = $('#speed-meter');
            if (!speedEl.length) {
                $(`<div id="speed-meter" class="text-[9px] text-gray-600 font-mono text-center py-1">${data.tps} t/s · ${data.tokens} tokens</div>`).insertBefore('#chat-container > .flex:last');
            } else {
                speedEl.text(`${data.tps} t/s · ${data.tokens} tokens`);
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

function saveSettings() {
    const sys = $('#setting-system').val();
    config.temperature = $('#setting-temp').val();
    $.ajax({
        url: '/api/config', type: 'POST', contentType: 'application/json',
        data: JSON.stringify({ system_prompt: sys }),
        success: () => { toggleSettings(); showToast('Settings saved', 'success'); }
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
}

function applyTemplate() {
    const val = $('#template-select').val();
    if (val) $('#setting-system').val(val);
}

function applyAccentColor(color) {
    $('#accent-color-display').text(color);
    document.documentElement.style.setProperty('--accent', color);
    localStorage.setItem('ln-accent', color);
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
    const s = prompt("Font size (e.g. 14px):", localStorage.getItem('ln-font-size') || '14px');
    if (s) { $('body').css('font-size', s); localStorage.setItem('ln-font-size', s); }
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
            appendMessage(x.role === 'user' ? 'user' : 'ai', x.content, `msg-${x.id}`, x.id, i);
            if (x.timestamp) {
                const bubble = $(`#wrapper-msg-${x.id}`).find('.text-gray-600.font-mono').first();
                if (bubble.length) bubble.text(timeAgo(x.timestamp));
            }
        });
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
    $('#chat-container').empty();
    $('#welcome-msg').removeClass('hidden');
    if (window.innerWidth < 768) toggleSidebar();
}

function scrollToBottom() { const c = document.getElementById('chat-container'); c.scrollTop = c.scrollHeight; }

function escapeHtml(t) { return t ? t.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;") : ''; }

function loadHistoryList() {
    $.get("/api/history", (s) => {
        const l = $("#history-list"); l.empty();
        let currentGroup = null;
        s.forEach(x => {
            if (x.group_id && x.group_id !== currentGroup) { currentGroup = x.group_id; }
            const projLabel = x.project_title ? `<span class="ml-2 text-[9px] bg-nothing-red px-1 rounded text-white opacity-70">${escapeHtml(x.project_title)}</span>` : '';
            const pinned = x.pinned === '1';
            const pinBtn = pinned
                ? `<button onclick="unpinSession(event,'${x.id}')" class="text-yellow-500 hover:text-white p-1" title="Unpin">📌</button>`
                : `<button onclick="pinSession(event,'${x.id}')" class="text-gray-500 hover:text-yellow-500 p-1" title="Pin">📌</button>`;
            const archiveBtn = x.archived
                ? `<button onclick="archiveSession(event,'${x.id}',false)" class="text-gray-500 hover:text-white p-1" title="Unarchive">📤</button>`
                : `<button onclick="archiveSession(event,'${x.id}',true)" class="text-gray-500 hover:text-yellow-500 p-1" title="Archive">📦</button>`;
            l.append(`<div class="history-item group relative flex items-center justify-between p-2 hover:bg-white/5 rounded-lg cursor-pointer transition border border-transparent hover:border-white/5 mx-1 my-0.5 ${x.archived ? 'opacity-50' : ''} ${pinned ? 'border-l-2 border-yellow-600' : ''}" onclick="loadSession('${x.id}')" data-sid="${x.id}" id="wrapper-session-${x.id}">
<input type="checkbox" class="history-item-checkbox hidden group-hover:inline-block ml-1 accent-nothing-red shrink-0" id="history-check-${x.id}" onclick="toggleSelect(event,'${x.id}')">
<div class="title-text truncate text-xs text-gray-400 font-mono flex-1 min-w-0" ondblclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')">${pinned ? '📌 ' : ''}${escapeHtml(x.title)}${projLabel}</div>
<div class="flex gap-0.5 opacity-0 group-hover:opacity-100 transition shrink-0">
${pinBtn}${archiveBtn}
<button onclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')" class="text-gray-500 hover:text-white p-1 text-xs">✎</button>
<button onclick="deleteSession(event,'${x.id}')" class="text-gray-500 hover:text-red-500 p-1 text-xs">×</button>
</div></div>`);
        });
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
function startRecording() {
    if (mediaRecorder) return;
    audioChunks = [];
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.ondataavailable = e => { if (e.data.size > 0) audioChunks.push(e.data); };
        mediaRecorder.onstop = () => {
            const blob = new Blob(audioChunks, { type: 'audio/wav' });
            const fd = new FormData();
            fd.append('audio', blob, 'recording.wav');
            $.ajax({
                url: '/api/audio/transcribe', type: 'POST', data: fd, contentType: false, processData: false,
                success: (res) => {
                    if (res.text) {
                        const inp = $('#user-input');
                        inp.val(inp.val() + ' ' + res.text);
                        inp.focus();
                    }
                },
                error: () => { showToast('Transcription failed. Is whisper model installed?', 'error'); }
            });
            stream.getTracks().forEach(t => t.stop());
            mediaRecorder = null;
            $('#record-btn').removeClass('text-red-500');
        };
        mediaRecorder.start();
        $('#record-btn').addClass('text-red-500');
    }).catch(() => { showToast('Microphone access denied', 'error'); });
}

function stopRecording() {
    if (mediaRecorder && mediaRecorder.state === 'recording') {
        mediaRecorder.stop();
    }
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
