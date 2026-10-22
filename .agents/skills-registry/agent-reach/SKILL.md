---
name: agent-reach
description: Universal internet research router across 16 platforms (Twitter, Reddit, YouTube, GitHub, Exa, Jina).
---

# Agent Reach — Universal Internet Capability Router

Agent Reach provides direct, multi-backend routing across 16 internet platforms (OpenCLI, platform CLIs, APIs, Jina Reader, yt-dlp, mcporter). When researching or reading live internet content, use this skill and follow the established platform routes instead of inventing ad-hoc scrapers.

---

## ⚡ Standing Rules

1. **Health Check Before Action**: For multi-backend or login-backed platforms (XiaoHongShu, Reddit, Bilibili, Twitter, Facebook, Instagram), run `agent-reach doctor --json` first if `agent-reach` is installed. Use a populated `active_backend`.
2. **Announce Active Channel**: State which platform and backend you are using (e.g., `Using agent-reach: YouTube via yt-dlp` or `Using agent-reach: Web via Jina Reader`) before fetching.
3. **Follow Reference Retry Chains**: On failure, inspect the fallback chains in [references/](./references/) rather than guessing flags or inventing endpoints.
4. **Multi-Source Synthesis**: For broad research tasks, collect across relevant channels (e.g., Exa for technical web docs, Twitter/Reddit for community opinions, GitHub for code implementations), then synthesize the findings.
5. **Read-Only Scope**: This skill is strictly for *fetching and analyzing* internet content. It does not perform automated posting, liking, or destructive writes.

---

## 🧭 Platform Routing Table

| User Intent | Platform | Method / Backend | Reference Guide |
|---|---|---|---|
| **Web Search** | Exa / Web | `mcporter call exa.web_search_exa query="..."` | [references/search.md](./references/search.md) |
| **Web Page Reader** | Any URL | `curl -s "https://r.jina.ai/<URL>"` | [references/web.md](./references/web.md) |
| **RSS Feeds** | RSS / Atom | `python3 -c "import feedparser; ..."` | [references/web.md](./references/web.md) |
| **Code & Repos** | GitHub | `gh search repos / gh issue list` | [references/dev.md](./references/dev.md) |
| **Video Subtitles** | YouTube | `yt-dlp --write-sub --write-auto-sub` | [references/video.md](./references/video.md) |
| **Video Search** | Bilibili | `bili search "<query>" --type video` | [references/video.md](./references/video.md) |
| **Podcasts** | Xiaoyuzhou | Audio download + Whisper transcription | [references/video.md](./references/video.md) |
| **Tech Forum** | V2EX | `curl -s "https://www.v2ex.com/api/topics/hot.json"` | [references/social.md](./references/social.md) |
| **Microblogging** | Twitter / X | `twitter search` or OpenCLI | [references/social.md](./references/social.md) |
| **Community Threads** | Reddit | `opencli reddit search` / `rdt search` | [references/social.md](./references/social.md) |
| **Social / Lifestyle** | XiaoHongShu | `opencli xiaohongshu search` | [references/social.md](./references/social.md) |
| **Social Media** | Facebook & Instagram | `opencli facebook search` / `opencli instagram user` | [references/social.md](./references/social.md) |
| **Career / Jobs** | LinkedIn & Boss直聘 | Jina Reader / `opencli` / Boss CDP | [references/career.md](./references/career.md) |
| **Financial / Stocks** | Xueqiu | `opencli xueqiu` or direct quote API | [references/finance.md](./references/finance.md) |

---

## 🚀 Zero-Config Quick Commands

```bash
# 1. Read any web page clean in Markdown format
curl -s "https://r.jina.ai/https://example.com/article"

# 2. Extract YouTube subtitles/transcripts without downloading video
yt-dlp --write-sub --write-auto-sub --skip-download -o "/tmp/%(id)s" "https://www.youtube.com/watch?v=VIDEO_ID"
cat /tmp/VIDEO_ID.*.vtt 2>/dev/null || cat /tmp/VIDEO_ID*.vtt

# 3. Search GitHub repositories with stars & metadata
gh search repos "query" --sort stars --limit 10

# 4. Search Bilibili videos (bili-cli, no login required)
bili search "query" --type video -n 5

# 5. Fetch hot discussions from V2EX
curl -s "https://www.v2ex.com/api/topics/hot.json" -H "User-Agent: agent-reach/1.0"

# 6. Parse an RSS or Atom feed
python3 -c "import feedparser; [print(f'{e.title} -> {e.link}') for e in feedparser.parse('https://news.ycombinator.com/rss').entries[:5]]"
```

---

## 🔐 Login-Backed Platforms (Desktop / OpenCLI)

For platforms requiring user sessions (Reddit, Twitter, XiaoHongShu, Facebook, Instagram):
- **Desktop OpenCLI**: Reuses the user's existing Chrome session without automating credentials or dumping passwords.
- **Twitter**: Requires user-exported cookies via `Cookie-Editor` configured in `TWITTER_AUTH_TOKEN` and `TWITTER_CT0`.
- **Boss直聘**: Uses an explicit dedicated Chrome profile via loopback CDP (`http://localhost:9222`).

```bash
# Search Reddit posts
opencli reddit search "topic bug" -f yaml

# Search Twitter posts
twitter search "query" -n 10

# Search XiaoHongShu notes
opencli xiaohongshu search "query" -f yaml

# Search Facebook groups & feeds
opencli facebook search "query" -f yaml
```

---

## 🩺 Diagnostics & Environment

```bash
# Run full multi-channel diagnostic check
agent-reach doctor --json 2>/dev/null || which agent-reach || which yt-dlp gh curl
```

When missing `agent-reach` CLI, you can invoke directly via:
- `pip install agent-reach` or `pipx install agent-reach`
- `uvx agent-reach doctor`
- Or use the zero-config direct CLI tools (`curl`, `yt-dlp`, `gh`, `feedparser`).
