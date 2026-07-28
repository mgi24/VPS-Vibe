# Discord Notifier Integration Notes

## Files

### Server (Discord Webhook Forwarder)
| File | Description |
|---|---|
| `/home/mamad/discord/server.js` | Bun HTTP server, receives notifications from OpenCode plugin and forwards to Discord webhook |
| `/home/mamad/discord/.env` | Environment variables: `DISCORD_WEBHOOK_URL`, `DISCORD_PORT`, `DISCORD_SECRET` |
| `/home/mamad/discord/package.json` | Package config for Bun |

### OpenCode Plugin
| File | Description |
|---|---|
| `/home/mamad/.config/opencode/plugins/discord-notify.js` | Plugin that hooks OpenCode events and sends notifications to the server |

### Systemd Service
| File | Description |
|---|---|
| `/etc/systemd/system/discord-notifier.service` | Systemd unit that runs the server on port 8016 |

### Documentation
| File | Description |
|---|---|
| `/home/mamad/doc.md` | Service registry — includes `discord-notifier.service` entry |

## How It Works

```
OpenCode event (permission.asked, session.idle, etc.)
    → discord-notify.js plugin
        → POST to localhost:8016/notify
            → server.js
                → Discord webhook
```

## Events Hooked
- `permission.asked` — Permission request with chat link
- `permission.replied` — Permission allowed/denied
- `session.created` — New session started
- `session.idle` — Session completed with summary (tools used, messages)
- `session.error` — Session error
- `question.asked` — AI asks user a question (via `tool.execute.before` hook)

## Setup Required
1. Fill `DISCORD_WEBHOOK_URL` in `/home/mamad/discord/.env`
2. `systemctl start discord-notifier.service`
3. Restart OpenCode to load the plugin
