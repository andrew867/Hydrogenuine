# Multi-chat and session guide

Hydrogenuine Community keeps independent chat histories in the local SQLite gateway store. Each chat has its own ID, title, messages, branch lineage, and receipt-related activity.

## Web UI

Open `http://127.0.0.1:4173` and use the Conversations panel.

- New chat creates and selects an empty chat.
- Selecting a chat resumes its saved history.
- Branch copies the current messages into a new chat and selects the branch.
- Retry repeats the last user turn with the deterministic provider.

The conversation list is reloaded from SQLite after a gateway restart.

## CLI

Create separate sessions:

```bash
hg chat new --title "Local provider experiments"
hg chat new --title "Document research"
```

List them:

```bash
hg chat list
```

The asterisk marks the last active CLI chat.

Resume and print a chat:

```bash
hg chat resume CHAT_ID
```

Send one turn to a saved chat:

```bash
hg chat resume CHAT_ID --message "Continue with the next bounded step."
```

Resume the last active CLI chat:

```bash
hg chat resume
```

Use JSON output for scripts:

```bash
hg chat list --json
hg chat resume CHAT_ID --json
```

## Data and limits

Native and Docker launchers use SQLite. A manual gateway launched with `HG_GATEWAY_STORE=memory` is intentionally temporary and will not preserve chats.

Chat persistence does not imply remote sync, multi-device sync, or hosted backup. The Community build stores data on the machine running the gateway. Back up the configured Community data directory if the local histories matter.

Separate browser windows can use the same local gateway and see the same chat list. This is shared local access, not managed multi-user tenancy.
