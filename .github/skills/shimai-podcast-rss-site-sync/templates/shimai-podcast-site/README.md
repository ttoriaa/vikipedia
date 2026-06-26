Shimai Podcast RSS Sync Template

Files in this template:
- scripts/rss-sync.mjs
- .github/workflows/rss-site-sync.yml

Quick setup in target repo:
1. Copy scripts/rss-sync.mjs to scripts/rss-sync.mjs.
2. Copy .github/workflows/rss-site-sync.yml to .github/workflows/rss-site-sync.yml.
3. Ensure your repo has an update command, for example npm run update:data.
4. Set repository variable PODCAST_RSS_URL.
5. Optional repository variables:
   - PODCAST_UPDATE_COMMAND (default: npm run update:data)
   - PODCAST_CHANGED_PATHS (default: public/data)

Manual test:
- Trigger workflow_dispatch and pass rss_url + update_command.
- Or run locally:
  node scripts/rss-sync.mjs --rss-url "https://example.com/feed.xml" --update-command "npm run update:data" --changed-paths "public/data"

Behavior:
- If HTTP 304 or same content hash, script exits with changed=false and skips commit.
- If RSS changed, script runs update command, validates outputs, updates .cache/rss_state.json, and workflow commits changes.
