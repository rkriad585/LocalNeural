// --- VARIABLES ---
const socket = io();
let currentSessionId = null;
let currentAiMessageId = null;
let isGenerating = false;
let autoScroll = true;
let attachedImageBase64 = null;
let activeProjectId = null;
let config = { temperature: 0.7 }; 

// --- INITIALIZATION ---
$(document).ready(function() {
    console.log("System Online");
    loadModels();
    loadHistoryList();
    loadSettings();
    loadLibrary();
    loadProjects();

    $('#chat-form').on('submit', handleFormSubmit);
    
    // FIX: Ensure form submission works for file uploads
    $('#project-form').on('submit', handleProjectSubmit);
    
    $('#user-input').on('keydown', (e) => {
        if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { 
            e.preventDefault(); 
            handleFormSubmit(e); 
        }
    });

    document.getElementById('user-input').addEventListener('paste', handlePaste);
    const dz = document.getElementById('user-input');
    dz.addEventListener('dragover', (e)=>{e.preventDefault();$(dz).addClass('border-nothing-red')});
    dz.addEventListener('dragleave', (e)=>{e.preventDefault();$(dz).removeClass('border-nothing-red')});
    dz.addEventListener('drop', (e)=>{e.preventDefault();$(dz).removeClass('border-nothing-red'); if(e.dataTransfer.files[0]) handleFileProcess(e.dataTransfer.files[0]);});

    $('#history-search').on('keyup', filterHistory);
    socket.on('title_updated', () => loadHistoryList());

    $(document).on('click', function(e) {
        if (!$(e.target).closest('.msg-bubble, .action-bar').length) {
            $('.action-bar').addClass('hidden');
        }
    });
});

// --- PROJECTS (FIXED) ---
function toggleProjectModal() { $('#project-modal').toggleClass('hidden'); }

// FUNCTION: handleProjectSubmit
// Used to upload files and create project
function handleProjectSubmit(e) {
    e.preventDefault();
    const btn = $(this).find('button[type="submit"]');
    btn.prop('disabled', true).text('Creating...');

    // Use FormData to handle file uploads correctly
    const formData = new FormData(this);

    $.ajax({
        url: '/api/projects',
        type: 'POST',
        data: formData,
        contentType: false, // Required for multipart/form-data
        processData: false, // Required for multipart/form-data
        success: (res) => {
            if(res.status === 'success') {
                toggleProjectModal();
                loadProjects();
                selectProject(res.id, formData.get('title'));
                this.reset();
            } else {
                alert("Error creating project: " + res.message);
            }
        },
        error: (err) => {
            alert("Upload Failed. Check console.");
            console.error(err);
        },
        complete: () => {
            btn.prop('disabled', false).text('Create Project');
        }
    });
}

function loadProjects() {
    $.get('/api/projects', (data) => {
        $('#projects-list').empty();
        data.forEach(p => {
            $('#projects-list').append(`
                <div onclick="selectProject('${p.id}', '${escapeHtml(p.title)}')" class="project-tag cursor-pointer bg-[#222] border border-white/5 px-2 py-1 rounded text-[10px] text-gray-400 hover:text-white hover:border-nothing-red truncate max-w-[100px] transition" title="${escapeHtml(p.title)}">
                    ${escapeHtml(p.title)}
                </div>
            `);
        });
    });
}

function selectProject(pid, title) {
    activeProjectId = pid;
    // UI Feedback
    $('#active-project-name').text(`PROJECT: ${title}`).removeClass('hidden');
    // Highlight selected
    $('.project-tag').removeClass('border-nothing-red text-white').addClass('text-gray-400 border-white/5');
    // (Optional: add visual logic to highlight the clicked one)
    
    // Start fresh chat in this project context
    newChat(true); // true = keep project ID
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

function sendMessage(overridePrompt = null, isEdit = false, msgId = null) {
    const $input = $('#user-input');
    const prompt = overridePrompt || $input.val().trim();
    const model = $('#model-select').val();

    if ((!prompt && !attachedImageBase64)) return;
    if (!model) { alert("Select a model first."); return; }

    $('#welcome-msg').addClass('hidden');
    let tempId = `temp-${Date.now()}`;
    const imgToSend = attachedImageBase64;

    if (!isEdit) {
        $input.val('').css('height', 'auto');
        $input.focus();
        appendMessage('user', prompt, tempId, null, imgToSend);
        if(attachedImageBase64) clearImage();
    }
    
    currentAiMessageId = `msg-${Date.now()}`;
    appendMessage('ai', '', currentAiMessageId);
    setGeneratingState(true);

    socket.emit('user_message', { 
        prompt: prompt, model: model, session_id: currentSessionId,
        project_id: activeProjectId, // Pass global active project ID
        system_prompt: config.custom_session_prompt || null,
        temperature: config.temperature,
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
            session_id: currentSessionId,
            model: model,
            temperature: config.temperature
        });
    }
}

// --- RENDERING ---
function appendMessage(role, text, domId, dbId = null, imgBase64 = null) {
    const isUser = role === 'user';
    const finalDomId = domId; 
    const dataAttr = dbId ? `data-db-id="${dbId}"` : '';
    const actionBar = `<div class="action-bar hidden absolute ${isUser ? '-top-8 right-0' : '-top-8 left-0'} bg-[#222] border border-white/20 rounded-lg flex items-center shadow-xl z-10 px-1 py-1 gap-1"><button onclick="copyMessage('${finalDomId}', this)" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Copy"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg></button>${isUser ? `<button onclick="startEdit('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Edit"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"></path></svg></button>` : `<button onclick="triggerRegenerate()" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Regenerate"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg></button>`}<button onclick="saveToLibraryFromMsg('${finalDomId}')" class="p-1.5 hover:bg-white/10 rounded text-gray-400 hover:text-white" title="Save to Library"><svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg></button></div>`;
    const imgHtml = imgBase64 ? `<img src="data:image/jpeg;base64,${imgBase64}" class="max-w-[200px] rounded-lg mb-2 border border-white/10 block">` : '';
    const cursor = !isUser && !text ? '<span class="typing-cursor"></span>' : '';
    const html = `<div class="flex gap-3 ${isUser ? 'flex-row-reverse' : ''} fade-in group max-w-3xl mx-auto relative mb-6" ${dataAttr} id="wrapper-${finalDomId}"><div class="w-8 h-8 rounded-full ${isUser ? 'bg-white' : 'bg-nothing-red'} flex items-center justify-center shrink-0 font-mono font-bold text-[10px] text-black shadow-lg border border-white/20 mt-1 select-none cursor-default">${isUser ? 'U' : 'AI'}</div><div class="relative max-w-[85%]">${actionBar}<div onclick="toggleActions('${finalDomId}')" class="msg-bubble cursor-pointer ${isUser ? 'bg-white/10' : 'bg-[#151515] border border-white/5'} rounded-2xl ${isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'} px-5 py-3 shadow-sm prose prose-invert break-words">${imgHtml}<div id="${finalDomId}" class="prose-content">${cursor}</div></div></div></div>`;
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
    if(data.temp_id) {
        const wrapper = $(`#wrapper-${data.temp_id}`);
        const content = document.getElementById(data.temp_id);
        if(wrapper.length) {
            wrapper.attr('data-db-id', data.db_id);
            wrapper.attr('id', `wrapper-msg-${data.db_id}`);
            content.id = `msg-${data.db_id}`;
            wrapper.find('.msg-bubble').attr('onclick', `toggleActions('msg-${data.db_id}')`);
            wrapper.find('button[title="Copy"]').attr('onclick', `copyMessage('msg-${data.db_id}', this)`);
            wrapper.find('button[title="Edit"]').attr('onclick', `startEdit('msg-${data.db_id}')`);
            wrapper.find('button[title="Save to Library"]').attr('onclick', `saveToLibraryFromMsg('msg-${data.db_id}')`);
        }
    }
});
socket.on('stream_chunk', (data) => {
    const aiDiv = document.getElementById(currentAiMessageId);
    if(aiDiv) {
        let raw = aiDiv.getAttribute('data-raw') || "";
        raw += data.chunk;
        aiDiv.setAttribute('data-raw', raw);
        aiDiv.innerHTML = marked.parse(raw) + '<span class="typing-cursor"></span>';
        highlightCode(aiDiv);
        if(autoScroll) scrollToBottom();
    }
});
socket.on('stream_done', () => {
    const aiDiv = document.getElementById(currentAiMessageId);
    if(aiDiv) {
        let raw = aiDiv.getAttribute('data-raw');
        aiDiv.innerHTML = marked.parse(raw);
        highlightCode(aiDiv);
        addCodeCopyButtons(aiDiv);
    }
    setGeneratingState(false);
});
socket.on('session_created', (data) => { currentSessionId = data.session_id; loadHistoryList(); });

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
    $.ajax({ url: '/api/config', type: 'POST', contentType: 'application/json', data: JSON.stringify({ system_prompt: sys }), success: () => { toggleSettings(); } });
}
function loadSettings() {
    $.get('/api/config', (data) => { $('#setting-system').val(data.system_prompt); });
    $('#setting-temp').val(config.temperature); $('#temp-display').text(config.temperature);
}
function loadSession(id) { 
    currentSessionId = id; 
    $.get(`/api/chat/${id}`, (data) => {
        $('#chat-container').empty(); 
        $('#welcome-msg').addClass('hidden'); 
        if (data.model) $('#model-select').val(data.model);
        
        // Restore Project Context if saved in session
        if (data.project_id) {
            activeProjectId = data.project_id;
            // Hacky way to get title: would ideally fetch from API, but for now just show generic
            $('#active-project-name').text(`PROJECT MODE`).removeClass('hidden');
        } else {
            activeProjectId = null;
            $('#active-project-name').addClass('hidden');
        }

        data.messages.forEach(x => { 
            let i = null; 
            if(x.images){ try{i=JSON.parse(x.images)[0];}catch(e){} } 
            appendMessage(x.role==='user'?'user':'ai', x.content, `msg-${x.id}`, x.id, i); 
        }); 
        if(window.innerWidth<768) toggleSidebar(); 
        scrollToBottom(); 
    }); 
}

// --- UTILS ---
function toggleLibrary() { $('#library-modal').toggleClass('hidden'); }
function loadLibrary() { $.get('/api/prompts', (d) => { $('#library-list').empty(); d.forEach(p => $('#library-list').append(`<div class="bg-[#151515] p-3 rounded border border-white/5 hover:border-white/20 flex justify-between items-start group"><div onclick="usePrompt('${escapeHtml(p.content)}')" class="cursor-pointer flex-1"><div class="font-bold text-sm text-gray-300">${escapeHtml(p.title)}</div><div class="text-xs text-gray-500 line-clamp-2 mt-1 font-mono">${escapeHtml(p.content)}</div></div><button onclick="deletePrompt(${p.id})" class="text-gray-600 hover:text-red-500 px-2">×</button></div>`)); }); }
function savePrompt() { const t=$('#new-prompt-title').val(); const c=$('#new-prompt-content').val(); if(t&&c)$.ajax({url:'/api/prompts',type:'POST',contentType:'application/json',data:JSON.stringify({title:t,content:c}),success:()=>{loadLibrary();$('#new-prompt-title').val('');$('#new-prompt-content').val('');}}); }
function deletePrompt(id) { $.ajax({url:`/api/prompts/${id}`, type:'DELETE', success:loadLibrary}); }
function usePrompt(text) { $('#user-input').val(text); toggleLibrary(); $('#user-input').focus(); }
function saveToLibraryFromMsg(id) { const text=document.getElementById(id).innerText; const title=prompt("Name:",text.substring(0,20)); if(title)$.ajax({url:'/api/prompts',type:'POST',contentType:'application/json',data:JSON.stringify({title:title,content:text}),success:()=>{alert("Saved");loadLibrary();}}); }
function copyMessage(id, btn) { const text=document.getElementById(id).innerText; if(navigator.clipboard&&window.isSecureContext){navigator.clipboard.writeText(text).then(()=>showCopied(btn));}else{const ta=document.createElement("textarea");ta.value=text;document.body.appendChild(ta);ta.select();try{document.execCommand('copy');showCopied(btn);}catch(e){}document.body.removeChild(ta);} }
function showCopied(btn) { const h=$(btn).html(); $(btn).html('✓'); setTimeout(()=>$(btn).html(h), 1500); }
function highlightCode(el) { el.querySelectorAll('pre code').forEach(b => hljs.highlightElement(b)); }
function addCodeCopyButtons(el) { $(el).find('pre').each(function(){ if($(this).find('.code-header').length===0){ const w=$('<div class="code-wrapper"></div>'); $(this).wrap(w); const h=$(`<div class="code-header"><span>code</span><span class="cursor-pointer hover:text-white transition copy-btn">COPY</span></div>`); h.find('.copy-btn').click(function(){ const c=$(this).closest('.code-wrapper').find('code').text(); const ta=document.createElement("textarea"); ta.value=c; document.body.appendChild(ta); ta.select(); try{document.execCommand('copy');showCopied(this);}catch(e){} document.body.removeChild(ta); }); $(this).closest('.code-wrapper').prepend(h); }}); }
function handleImageSelect(input) { if (input.files && input.files[0]) handleFileProcess(input.files[0]); }
function handleFileProcess(file) { const r = new FileReader(); r.readAsDataURL(file); r.onload = (e) => { const i = new Image(); i.src = e.target.result; i.onload = () => { const c = document.createElement('canvas'); const s = 800 / i.width; c.width = 800; c.height = i.height * s; const x = c.getContext('2d'); x.drawImage(i, 0, 0, c.width, c.height); const d = c.toDataURL('image/jpeg', 0.7); attachedImageBase64 = d.split(',')[1]; $('#preview-src').attr('src', d); $('#img-preview').removeClass('hidden'); } } }
function handlePaste(e) { const items = (e.clipboardData || e.originalEvent.clipboardData).items; for(let i in items){ if(items[i].kind==='file' && items[i].type.startsWith('image/')){ handleFileProcess(items[i].getAsFile()); e.preventDefault(); } } }
function clearImage() { attachedImageBase64=null; $('#img-upload').val(''); $('#img-preview').addClass('hidden'); }
function toggleAutoScroll() { autoScroll = !autoScroll; $('#autoscroll-btn').toggleClass('hidden', autoScroll); if(autoScroll) scrollToBottom(); }
function checkScroll() { const el=document.getElementById('chat-container'); const b=el.scrollHeight-el.scrollTop-el.clientHeight<50; if(!b){autoScroll=false;$('#autoscroll-btn').removeClass('hidden');}else{autoScroll=true;$('#autoscroll-btn').addClass('hidden');} }
function setGeneratingState(gen) { isGenerating=gen; const b=$('#action-btn'); if(gen){ $('#icon-send').addClass('hidden');$('#icon-stop').removeClass('hidden'); b.addClass('bg-nothing-red text-white').removeClass('bg-white text-black');}else{ $('#icon-send').removeClass('hidden');$('#icon-stop').addClass('hidden'); b.removeClass('bg-nothing-red text-white').addClass('bg-white text-black');} }
function toggleSidebar() { $('#sidebar').toggleClass('-translate-x-full'); $('#mobile-overlay').toggleClass('hidden'); }
function filterHistory() { const val=$(this).val().toLowerCase(); $('.history-item').each(function(){ $(this).toggle($(this).text().toLowerCase().indexOf(val)>-1); }); }
function renameChat(e,id,old) { e.stopPropagation(); const n=prompt("Rename:",old); if(n)$.ajax({url:'/api/rename',type:'POST',contentType:'application/json',data:JSON.stringify({id:id,title:n}),success:loadHistoryList}); }
function deleteSession(e,id) { e.stopPropagation(); if(confirm('Delete trace?')) $.ajax({url:`/api/delete/${id}`,type:'DELETE',success:loadHistoryList}); }
function newChat(keepProject = false) { 
    currentSessionId=null; 
    config.custom_session_prompt = null; 
    if(!keepProject) {
        activeProjectId=null; 
        $('#active-project-name').addClass('hidden');
        $('.project-tag').removeClass('text-gray-400 border-white/5').addClass('text-gray-400 border-white/5'); // Reset styles
    }
    $('#chat-container').empty(); 
    $('#welcome-msg').removeClass('hidden'); 
    if(window.innerWidth<768) toggleSidebar(); 
}
function scrollToBottom() { const c=document.getElementById('chat-container'); c.scrollTop=c.scrollHeight; }
function escapeHtml(t) { return t?t.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"): ''; }
function loadHistoryList() { $.get("/api/history", (s) => { const l=$("#history-list"); l.empty(); s.forEach(x => { const projLabel = x.project_title ? `<span class="ml-2 text-[9px] bg-nothing-red px-1 rounded text-white opacity-70">${escapeHtml(x.project_title)}</span>` : ''; l.append(`<div class="history-item group relative flex items-center justify-between p-3 hover:bg-white/5 rounded-lg cursor-pointer transition border border-transparent hover:border-white/5 mx-2 my-1" onclick="loadSession('${x.id}')"><div class="title-text truncate text-xs text-gray-400 font-mono w-full pr-12" ondblclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')">${escapeHtml(x.title)}${projLabel}</div><div class="absolute right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition"><button onclick="renameChat(event,'${x.id}','${escapeHtml(x.title)}')" class="text-gray-500 hover:text-white p-1">✎</button><button onclick="deleteSession(event,'${x.id}')" class="text-gray-500 hover:text-red-500 p-1">×</button></div></div>`); }); }); }
function loadModels() { $.get("/api/models", (d) => { const s=$("#model-select"); s.empty(); if(d.models) d.models.forEach(m=>s.append(`<option value="${m.name}">${m.name}</option>`)); else s.append(`<option>Ollama Down</option>`); }); }
function exportChat(f) { if(!currentSessionId){alert("Open chat first.");return;} if(f==='html'){ window.open(`/api/export/${currentSessionId}?format=html`,'_blank'); } else { window.location.href=`/api/export/${currentSessionId}?format=${f}`; }}
function toggleSessionSettings() { const p = prompt("System Prompt for THIS chat:", config.custom_session_prompt || "Default"); if(p!==null) { if(currentSessionId) { $.ajax({ url: `/api/session/${currentSessionId}/config`, type: 'POST', contentType: 'application/json', data: JSON.stringify({ system_prompt: p }), success: () => alert("Updated session.") }); } else { config.custom_session_prompt = p; alert("Applied to next new chat."); } } }
