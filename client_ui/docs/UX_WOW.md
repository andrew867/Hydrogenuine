# UX wow checklist

This scaffold implements the core layout and the three pillars of "wow":
1) Fast and clean chat UI
2) Multi-agent visibility (right panel)
3) Human approvals (separate queue)

Implemented polish (UI enhancements):
- Token streaming in the chat bubbles with partial rendering and cursor glow
- Inline tool cards that expand into a full "Run timeline" drawer (Timeline / Hide toggle)
- Message actions: copy, retry (resend last user message)
- Per-message "Approval required" and "Policy" badges (when API provides or assistant reply)

Suggested next polish steps:
- Message actions: pin, share, branch conversation
- Voice input (Web Speech API), optional TTS playback
- Gesture navigation for mobile, swipe from left to open chat list
- Offline caching of chat list and last 50 messages (service worker)
- Auth: passkeys, device binding, short-lived tokens
