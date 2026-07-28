import { serve } from "bun"

const WEBHOOK_URL = process.env.DISCORD_WEBHOOK_URL || ""
const PORT = parseInt(process.env.DISCORD_PORT || "8016")
const SECRET = process.env.DISCORD_SECRET || "opencode-secret"

const DISCORD_LIMIT = 2000

function truncate(text, max) {
  if (text.length <= max) return text
  return text.slice(0, max - 3) + "..."
}

function buildEmbed(title, description, color, fields) {
  const embed = {
    title: truncate(title, 256),
    description: truncate(description || "", 1024),
    color: color || 5814783,
    timestamp: new Date().toISOString(),
    footer: { text: "OpenCode Notifier" },
  }
  if (fields && fields.length) {
    embed.fields = fields.slice(0, 25).map(f => ({
      name: truncate(f.name, 256),
      value: truncate(f.value, 1024),
      inline: f.inline || false,
    }))
  }
  return embed
}

async function sendToDiscord(content, embed) {
  if (!WEBHOOK_URL) {
    console.error("DISCORD_WEBHOOK_URL not set")
    return { error: "Webhook URL not configured" }
  }

  const payload = {}
  if (content) payload.content = truncate(content, 2000)
  if (embed) payload.embeds = [embed]

  try {
    const res = await fetch(WEBHOOK_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
    if (!res.ok) {
      const err = await res.text()
      console.error("Discord error:", res.status, err)
      return { error: `Discord returned ${res.status}`, details: err }
    }
    return { success: true }
  } catch (err) {
    console.error("Fetch error:", err)
    return { error: err.message }
  }
}

const server = serve({
  port: PORT,
  async fetch(req) {
    const path = new URL(req.url).pathname
    if (req.method === "POST" && path === "/notify") {
      const auth = req.headers.get("authorization") || ""
      if (auth !== `Bearer ${SECRET}`) {
        return new Response("Unauthorized", { status: 401 })
      }

      let body
      try {
        body = await req.json()
      } catch {
        return new Response("Invalid JSON", { status: 400 })
      }

      const { type, title, description, fields, color, content } = body

      let embed = null
      if (title) {
        const themeColors = {
          "permission.asked": 16755371,
          "permission.replied": 3066993,
          "session.idle": 3082472,
          "session.created": 5763719,
          "session.error": 15158332,
          "question.asked": 15105180,
        }
        embed = buildEmbed(title, description, color || themeColors[type] || 5814783, fields)
      }

      const result = await sendToDiscord(content || null, embed)
      return Response.json(result)

    } else if (req.method === "GET" && path === "/health") {
      return Response.json({ status: "ok", webhook: !!WEBHOOK_URL })

    } else {
      return new Response("Not Found", { status: 404 })
    }
  },
})

console.log(`Discord notifier listening on port ${PORT}`)
