---
name: whatsapp
description: "Use the globally configured WhatsApp Translator MCP to check connection status; list or find contacts and groups; read, search, summarize, or retrieve recent WhatsApp messages; prepare translated messages; send or reply after preview and confirmation; react to messages; or mark conversations read. Trigger for requests involving the user's WhatsApp account, chats, contacts, received messages, outgoing messages, replies, reactions, read receipts, or WhatsApp translation."
---

# Whatsapp

Use the `whatsapp-translator` MCP server at `https://whatsapp-translator-production.up.railway.app/mcp`. Keep reads convenient and writes deliberate.

## Guardrails

- Treat `get_status`, `list_contacts`, `search_contacts`, `read_messages`, and `search_messages` as read-only.
- Treat `send_message`, `reply_to_message`, `react_to_message`, and `mark_conversation_read` as external writes.
- Never expose raw contact IDs, JIDs, message IDs, preparation tokens, or idempotency keys unless the user asks or they are needed to diagnose a failure.
- Never guess between ambiguous contacts. Show the matching names and ask the user to choose.
- Never mark a chat read merely because it was inspected.
- Preserve message wording when quoting. Clearly identify translated text when the distinction matters.

## Connect and authorize

1. Call `get_status` when connection state matters or another tool reports a connection problem.
2. If the MCP server or tools are unavailable, explain that the globally configured server may need reconnection in a new task or Codex restart.
3. If read tools are missing, reconnect with `whatsapp.read`.
4. If send tools are missing, reconnect with both `whatsapp.read` and `whatsapp.send`.
5. Do not request send access for a read-only task.

## Find conversations

- Use `search_contacts` before selecting a recipient by name or number.
- Use `list_contacts` for recent chats, groups, unread chats, or pagination.
- Prefer display names in responses; use IDs only in subsequent tool calls.
- Read recent context with `read_messages` before drafting a reply unless the user's request already provides sufficient context.

## Read and search messages

### Read one conversation

1. Resolve the conversation with `search_contacts`.
2. Call `read_messages` with its `contact_id`.
3. Set `direction` to `incoming` or `outgoing` when the user asks for one side only.
4. Follow `nextCursor` only when more history is needed.
5. Present timestamps in the user's local timezone and state the timezone when ambiguity matters.

### Search by text

Call `search_messages` only with a non-empty `query`. Add contact, direction, time, and limit filters when useful. Never use an empty query as a shortcut for recent messages.

### Get the latest messages across all conversations

The server has no single global-latest endpoint. To answer requests such as “show my last 10 received messages”:

1. Call `list_contacts`, ordered by recent activity, with enough results to cover active chats.
2. Read a small recent page from each plausible conversation with `direction: incoming`.
3. If the requested count is not covered, paginate contacts and repeat.
4. Merge all incoming results, deduplicate by message ID, sort by timestamp descending, and take the requested count.
5. Return sender, local time, and text. Add the group or conversation name when it prevents confusion.

Do not treat the most recent ten conversations as the most recent ten messages.

## Prepare and send text safely

Always use this sequence for a new message or reply:

1. Resolve the exact recipient with `search_contacts`.
2. Read context when relevant.
3. Call `prepare_message` with the recipient, source text, and optional reply target.
4. Show the user the resolved recipient and exact `finalText`. State whether it was translated and the target language.
5. Ask for confirmation before sending unless the user has already confirmed that exact recipient and exact final text after seeing the preview.
6. After confirmation, promptly call `send_message` or `reply_to_message` because the preparation token is short-lived.
7. Generate a unique idempotency key of at least eight characters. Reuse it only when retrying the identical operation; use a new key if recipient, content, or reply target changes.
8. Report the confirmed send result. Never claim success from preparation alone.

### Translation modes

- Use `auto` by default. It follows the conversation's configured target language.
- Use `required` when the user explicitly requires translation. Supply `target_language` when they name it.
- Use `never` only when the user explicitly wants the original text sent unchanged or no translation is necessary.
- If `auto` or `required` translation is unavailable, errors, or returns empty text, stop. Never retry with `never`, and never send the English source as a fallback.
- If a preparation expires, prepare again and show the new final preview before sending.

## Reply, react, and mark read

- For a reply, identify the exact message using `read_messages`, pass its ID as `reply_to_message_id` to `prepare_message`, preview, confirm, then call `reply_to_message`.
- For a reaction, identify the exact message, show the intended emoji and target, then call `react_to_message` only when authorized. Use an empty emoji only when the user explicitly wants to remove their reaction.
- Call `mark_conversation_read` only when the user explicitly asks. Include a message ID only when a WhatsApp read receipt should be sent for that stored message.

## Available tools

- `get_status`
- `list_contacts`
- `search_contacts`
- `read_messages`
- `search_messages`
- `prepare_message`
- `send_message`
- `reply_to_message`
- `react_to_message`
- `mark_conversation_read`

When tool schemas differ from this guide, follow the live schema while preserving these safety rules.
