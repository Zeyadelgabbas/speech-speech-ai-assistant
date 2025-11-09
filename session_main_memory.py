# In main.py (simplified)

# Initialize at session start
session_memory = SessionMemory(max_messages=30)

# Main loop
while True:
    # Record and transcribe
    audio = recorder.record_fixed_duration(5.0)
    user_text = stt.transcribe(audio)["text"]
    
    # Build messages
    messages = [
        {"role": "system", "content": system_prompt},
        *session_memory.get_messages_for_llm(),  # ← Conversation history
        {"role": "user", "content": user_text}
    ]
    
    # Call LLM
    response = llm_client.chat(messages, tools=tools)
    
    # Add to memory
    session_memory.add_message("user", user_text)
    session_memory.add_message("assistant", response["content"])
    
    # If tool calls, execute and add results
    if response["tool_calls"]:
        for tc in response["tool_calls"]:
            result = execute_tool(tc)
            session_memory.add_tool_result(tc["id"], tc["name"], result)
    
    # TTS and play
    tts_audio = tts.synthesize(response["content"])
    player.play(tts_audio)