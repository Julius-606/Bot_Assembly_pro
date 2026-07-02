# Major Update: Autonomy, AI Transparency, and Logging (v3.0.0)

This plan outlines the enhancements to the TURTLE bot to improve its resilience (MT5 retry), transparency (detailed AI update messages), and traceability (marking AI-driven changes in Google Sheets).

## User Review Required

- **MT5 Retry Interval**: I've set it to 5 minutes as requested. The bot will remain responsive to Telegram commands during this time.
- **AI Reasoning**: The AI will now be asked to provide a brief explanation and parameter highlights. This will be included in the "ORACLE UPDATE" message.
- **Marker Symbol**: Using '🕹' as the marker for the first trade after an AI update.

## Proposed Changes

### [Core Bot Logic]

#### [main.py](file:///C:/Users/Administrator/Jay/Bot_Assembly_pro/Turtle/main.py)

- **Version Update**: Increment version to `v3.0.0`.
- **MT5 Resilience**:
    - Wrap the initial MT5 startup in a loop or move it inside the main loop with a state check.
    - Implement a 5-minute timer for reconnection attempts.
    - Ensure Telegram command processing happens even if `broker.connected` is `False`.
- **AI Change Marker**:
    - Before executing a trade, check `my_cloud.state['ai_change_pending']`.
    - If `True`, prepend "🕹 " to the trade comment and set the flag to `False`.

---

### [AI Coach]

#### [coach.py](file:///C:/Users/Administrator/Jay/Bot_Assembly_pro/Turtle/src/coach.py)

- **Prompt Enhancement**: Update the AI prompt in `consult_oracle` to request reasoning and parameter changes in a structured format (e.g., JSON with `strategy_state` and `explanation` fields).
- **Message Enrichment**: Parse the new AI response format and include the reasoning/parameters in the Telegram notification.
- **State Trigger**: Set `self.cloud.state['ai_change_pending'] = True` whenever the strategy file is updated by the AI.

---

### [Cloud/Logging]

#### [cloud.py](file:///C:/Users/Administrator/Jay/Bot_Assembly_pro/Turtle/src/cloud.py)

- **Memory State**: Ensure `ai_change_pending` is part of the default state and managed correctly in `load_memory`/`save_memory`.

## Verification Plan

### Automated Tests
- No specific unit tests exist for these components, but I will simulate failures and triggers.

### Manual Verification
1. **MT5 Retry**:
    - Force disconnect MT5 (e.g., by providing a wrong password temporarily or killing the process).
    - Verify that the bot sends a "Connection Failed" message but continues to respond to `/status` command in Telegram.
    - Wait 5 minutes and verify it tries to reconnect.
2. **AI Transparency**:
    - Force an AI update using the `consult` command.
    - Verify the Telegram message contains the new detailed information (Reasoning, Parameters).
3. **Logging Marker**:
    - After an AI update, trigger a trade (or wait for one).
    - Check the Google Sheet (Sheet2) to verify the "🕹" symbol appears in the Strategy column for that trade.
    - Verify subsequent trades do NOT have the symbol.
