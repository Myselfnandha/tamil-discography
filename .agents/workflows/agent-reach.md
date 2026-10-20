---
description: Universal internet research & multi-platform retrieval router (Twitter, Reddit, YouTube, GitHub, Bilibili, XiaoHongShu, Exa, Jina). Invoke with /agent-reach or /reach.
---

# /agent-reach — Universal Internet Research Router

You are now in **AGENT REACH MODE**. Your task is to search, retrieve, and synthesize live internet information across 16 platforms with zero hallucination.

## Research Target
$ARGUMENTS

---

## Capabilities & Channels

| Channel | Platform | Protocol | Best For |
|---|---|---|---|
| **Web Search** | Exa AI | `mcporter call exa.web_search_exa` | Technical docs, official guides, AI frameworks |
| **Clean Reader** | Any URL | `curl -s "https://r.jina.ai/<URL>"` | LLM-ready markdown extraction of any web article |
| **Developer** | GitHub | `gh search repos / gh issue list` | Code repositories, issues, release notes |
| **Video Transcripts** | YouTube | `yt-dlp --write-sub --skip-download` | Video tutorials, conference talks, tech keynotes |
| **Bilibili** | Bilibili | `bili search "<query>" --type video` | Tech tutorials, benchmarks, developer reviews |
| **Social / Community** | Reddit / X | `opencli reddit` / `twitter search` | Real user sentiment, bug reports, workarounds |
| **Social / Lifestyle** | XiaoHongShu | `opencli xiaohongshu search` | Consumer reviews, tutorials, user feedback |
| **Tech Forum** | V2EX | `https://www.v2ex.com/api/topics/hot.json` | Developer trends, tech discussions |
| **Podcasts** | Xiaoyuzhou | Audio extract + Whisper transcription | Tech podcast episodes and interview transcripts |
| **Finance** | Xueqiu | Stock quotes & investor sentiment | Market reports and financial data |

---

## 3-Stage Reach Pipeline

### STAGE 1: CHANNEL SELECTION & HEALTH PROBE
1. Parse user query to determine target platform(s).
2. Check available tools:
   ```bash
   agent-reach doctor --json 2>/dev/null || which yt-dlp gh curl
   ```
3. Announce active platform route:
   > "Using Agent Reach: [Platform] via [Backend]"

### STAGE 2: MULTI-CHANNEL RETRIEVAL
- **Web Pages**: Fetch markdown directly using Jina Reader:
  ```bash
  curl -s "https://r.jina.ai/<URL>"
  ```
- **YouTube Subtitles**:
  ```bash
  yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" "<URL>"
  ```
- **GitHub Repos**:
  ```bash
  gh search repos "<query>" --sort stars --limit 10
  ```
- **Community Sentiments**:
  ```bash
  opencli reddit search "<query>" -f yaml 2>/dev/null || rdt search "<query>"
  ```

### STAGE 3: SYNTHESIS & CITATIONS
1. Synthesize multi-source findings clearly into key takeaways.
2. Link every factual claim to its source URL (`https://...`).
3. If any source failed or was blocked, declare the limitation transparently without guessing.
