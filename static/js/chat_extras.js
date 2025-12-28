// Function to handle regeneration
function triggerRegenerate() {
    if (!currentSessionId) return;
    
    // UI Update: Remove last message visually immediately
    const lastMsg = $('#chat-container').children().last();
    // Only remove if it's an AI message
    if (lastMsg.find('.bg-nothing-red').length > 0) {
        lastMsg.remove();
        
        // Setup new AI container
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

// Function to open Session Specific Settings
function toggleSessionSettings() {
    const p = prompt("Set System Prompt for THIS chat only:", config.system);
    if(p !== null) {
        // If chat exists, update in DB
        if(currentSessionId) {
            $.ajax({
                url: `/api/session/${currentSessionId}/config`,
                type: 'POST',
                contentType: 'application/json',
                data: JSON.stringify({ system_prompt: p }),
                success: () => alert("Updated for this session.")
            });
        } else {
            // If new chat (not started), just update local config temporarily
            config.custom_session_prompt = p;
            alert("Will be applied when you send the first message.");
        }
    }
}
