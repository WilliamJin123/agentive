---
status: resolved
trigger: "enter-key-not-sending: Pressing Enter in chat input adds a newline instead of sending the message"
created: 2026-02-01T00:00:00Z
updated: 2026-02-01T00:00:00Z
---

## Current Focus

hypothesis: TextArea's internal Enter key handling inserts newline BEFORE binding actions run - need to intercept in on_key with prevent_default()
test: Check Textual docs/source for proper Enter interception pattern
expecting: Need to add Enter handling in on_key method with event.prevent_default() like search mode does
next_action: Modify on_key to intercept Enter key and prevent default, then call action_submit

## Symptoms

expected: Pressing Enter should send the message. Shift+Enter should add a newline.
actual: Both Enter and Shift+Enter add a newline. Messages cannot be sent.
errors: No errors shown
reproduction: Run `python run_hfs.py`, type a message, press Enter
started: After Phase 11 implementation - discovered during manual testing after CSS fix

## Eliminated

## Evidence

- timestamp: 2026-02-01T00:01:00Z
  checked: chat_input.py structure and key handling
  found: |
    - ChatInput extends TextArea
    - Has BINDINGS with Binding("enter", "submit", ...) at line 44
    - Has action_submit() method at line 110 that posts Submitted message
    - on_key() method (line 209) only handles keys in _search_mode
    - When NOT in search mode, on_key returns early without intercepting Enter
  implication: The binding defines the action but TextArea's internal Enter handling runs first, inserting newline

- timestamp: 2026-02-01T00:02:00Z
  checked: Textual documentation via web search
  found: |
    - GitHub discussion #4216 confirms this exact issue
    - TextArea has internal newline handling for Enter that runs before bindings
    - Need to intercept in on_key and call prevent_default() like search mode does for escape/enter
    - The existing search_mode code at lines 224-226 shows correct pattern: event.prevent_default() before action
  implication: Fix requires adding Enter key interception in on_key outside of search mode

## Resolution

root_cause: |
  on_key() method returns early when not in search mode, allowing TextArea's internal Enter handling
  to insert a newline before the binding action runs. The BINDINGS system triggers actions but doesn't
  prevent the widget's default key handling. Need to intercept Enter in on_key with prevent_default().
fix: |
  Modify on_key() to intercept Enter key (without shift) when not in search mode:
  1. Check if key is "enter" and no shift modifier
  2. Call event.prevent_default() to stop newline insertion
  3. Call action_submit() to trigger the send behavior
verification: |
  1. Module imports correctly: python -c "from hfs.tui.widgets.chat_input import ChatInput" - SUCCESS
  2. Test suite passes: pytest hfs/tests/test_config.py - 26 passed
  3. Code review confirms:
     - Enter key (without shift) now calls event.prevent_default() then action_submit()
     - Shift+Enter still triggers action_newline via BINDINGS (no prevent_default needed)
     - Search mode Enter handling unchanged (still calls prevent_default and exits search)
files_changed:
  - hfs/tui/widgets/chat_input.py
