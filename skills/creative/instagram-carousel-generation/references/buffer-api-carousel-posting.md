# Buffer API for Carousel Posting

## Buffer API Overview

- **Type**: GraphQL (not REST)
- **Base URL**: `https://api.bufferapp.com/1/graphql` (or via `https://api.buffer.com/1/graphql`)
- **Auth**: Access token from `https://buffer.com/developers` → My Access Token
- **Docs**: `https://developers.buffer.com/guides/posts-and-scheduling.html`

## Required Token

Get from: https://buffer.com/developers → Account → API Keys / My Access Token

## Key Mutations

### Create Carousel Post (Instagram)

```graphql
mutation CreateCarouselPost($input: CreatePostInput!) {
  createPost(input: $input) {
    ... on PostActionSuccess {
      post {
        id
        dueAt
        status
        channelId
      }
    }
    ... on MutationError {
      message
    }
  }
}
```

**Variables:**
```json
{
  "input": {
    "text": "Caption text here...",
    "channelId": "INSTAGRAM_CHANNEL_ID",
    "schedulingType": "automatic",
    "mode": "addToQueue",
    "media": {
      "images": [
        "https://url-to-slide-1.png",
        "https://url-to-slide-2.png",
        "https://url-to-slide-3.png",
        "https://url-to-slide-4.png",
        "https://url-to-slide-5.png",
        "https://url-to-slide-6.png",
        "https://url-to-slide-7.png"
      ]
    }
  }
}
```

### Get Channels (to find Instagram channel ID)

```graphql
query GetChannels($organizationId: ID!) {
  channels(input: { organizationId: $organizationId }) {
    edges {
      node {
        id
        service { id username }
        channelId
        status
      }
    }
  }
}
```

## Python Example

```python
import requests
import json

BUFFER_TOKEN = "your_access_token"
GRAPHQL_URL = "https://api.buffer.com/1/graphql"

headers = {
    "Authorization": f"Bearer {BUFFER_TOKEN}",
    "Content-Type": "application/json"
}

def get_channels(org_id):
    query = """
    query GetChannels($organizationId: ID!) {
      channels(input: { organizationId: $organizationId }) {
        edges {
          node {
            id
            service { id username }
            channelId
            status
          }
        }
      }
    }
    """
    resp = requests.post(GRAPHQL_URL, headers=headers, json={"query": query, "variables": {"organizationId": org_id}})
    return resp.json()

def schedule_carousel(org_id, channel_id, caption, image_urls):
    mutation = """
    mutation CreateCarouselPost($input: CreatePostInput!) {
      createPost(input: $input) {
        ... on PostActionSuccess { post { id dueAt status channelId } }
        ... on MutationError { message }
      }
    }
    """
    variables = {
        "input": {
            "text": caption,
            "channelId": channel_id,
            "schedulingType": "automatic",
            "mode": "addToQueue",
            "media": {"images": image_urls}
        }
    }
    resp = requests.post(GRAPHQL_URL, headers=headers, json={"query": mutation, "variables": variables})
    return resp.json()
```

## Image Hosting Requirements

- Buffer requires **publicly accessible HTTPS URLs** for carousel images
- Cloudflare quick tunnels (`trycloudflare.com`) work but **change on restart**
- For production: use stable hosting (S3, Netlify, Vercel, GitHub Pages, Imgur, etc.)
- Images must be 1080x1350 (4:5) for Instagram carousel

## Agent Reach Note

**Agent Reach does NOT have Buffer integration.** It is read-only (search/read across 15 platforms). From its skill: *"NOT for: posting/commenting/liking (write operations)"*

To post carousels to Buffer, use direct GraphQL API calls as shown above.

## Carousel Caption Template (for AI Coding Agents topic)

```
7 AI Coding Agents That Ship Code While You Sleep 🤖

Stop writing boilerplate. Let agents handle the grind.

1. Claude Code — The OG (free tier, native Git worktrees)
2. Cursor — IDE-Native ($20/mo, Cmd+K editing)
3. Aider — Terminal-First (free, Git-aware)
4. Codex — Cloud Agents ($20/mo, sandboxed VMs)
5. OpenCode — Local-First (free, Ollama support)

Pick your stack:
• Features → Claude Code
• Quick edits → Cursor
• Terminal flow → Aider
• Async delegation → Codex
• Offline/private → OpenCode

Save 🔖 Follow @kunalsharmadec6 for more dev workflow tips

#AICoding #ClaudeCode #Cursor #Aider #Codex #OpenCode #DevTools #Productivity
```

## Scheduling Options

| Scheduling Type | Use Case |
|-----------------|----------|
| `automatic` + `addToQueue` | Add to posting schedule (optimal times) |
| `automatic` + `postNow` | Post immediately |
| `manual` + `dueAt` | Specific date/time |

## Rate Limits

- 100 requests/hour per token (generous for carousel posting)
- Carousel counts as 1 post with multiple media items
- Monitor `x-rate-limit-remaining` header