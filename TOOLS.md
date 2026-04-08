# Tools & Operational Warnings

## Tool Inventory

These are the tools installed on this machine. Use them directly — don't install skills that duplicate them.

### Browser Automation (Playwright + Chromium)
- What: Full browser control — navigate, click, type, screenshot, scrape
- When: Reward apps, shopping, ordering, any website interaction, form filling, price checking
- How:
 - Start: openclaw browser start
 - Navigate: openclaw browser navigate <url>
 - Snapshot: openclaw browser snapshot (get element refs)
 - Click: openclaw browser click <ref>
 - Type: openclaw browser type <text>
 - Screenshot: openclaw browser screenshot
- Notes:
 - Element refs expire on page change — always re-snapshot after navigation
 - Chromium path: ~/.cache/ms-playwright/chromium-1217/chrome-linux64/chrome
 - Config: headless true, noSandbox true, defaultProfile openclaw
 - For ordering: show Trey a summary and wait for confirmation before checkout

### Docker
- What: Container management for isolated services
- When: Running N8N, deploying new services, isolating workloads
- How: Standard docker CLI (docker ps, docker run, docker logs, etc.)
- Notes: Prefer Docker for new services over bare-metal installs

### N8N (Workflow Automation)
- What: Visual workflow builder for multi-step automations
- Where: Running in Docker on port 5678
- When: Complex multi-step workflows, webhook triggers, API chains, scheduled tasks beyond simple cron
- How: Access at http://localhost:5678 or configure via API
- Notes: Document all workflows you create. Test before enabling.

### Claude Code
- What: CLI tool for autonomous coding — writes, tests, and runs code
- When: Complex coding tasks, refactoring, building new tools, debugging
- How: claude command in terminal
- Notes: Uses Anthropic API (costs money per use). Use for complex tasks, not simple scripts you can write yourself.

### Shell / System
- What: Full sudo access to Ubuntu Server
- When: Package management, service control, file operations, system diagnostics
- How: Any shell command via exec tool
- Notes: You have passwordless sudo. Use it for system-level tasks.

### GitHub (gh CLI)
- What: GitHub interaction from command line
- When: Managing repos, issues, PRs, cloning projects
- How: gh CLI commands (needs auth setup first — not yet configured)
- Notes: Skill installed but gh auth not completed yet.

### Web Search (Perplexity via OpenRouter)
- What: AI-powered web search
- When: Research, fact-checking, finding current information
- How: Built-in OpenClaw web search tool
- Notes: Routes through OpenRouter, costs tokens per search.

### Storage
- Three-tier system:
 - Fast SSD (OS drive): ~/.openclaw/ — OpenClaw config, workspace, active data
 - Workspace SSD: /mnt/workspace — large files, browser profiles, project data
 - Archive HDD: /mnt/archive — old memory logs, transcripts, backups
 - Archive subdirs: /mnt/archive/memory, /mnt/archive/transcripts, /mnt/archive/backups

### Tailscale
- What: Encrypted mesh VPN connecting to Clanker's VPS
- This machine: 100.112.160.53
- When: Multi-agent coordination with Clanker (future)
- Notes: Running in background. No action needed unless setting up inter-bot communication.

## Tool Selection Guide

When Trey asks you to do something, pick the right tool:

- "Check my Panda Express rewards" → Browser (Playwright)
- "Find me deals on fishing rods" → Web search + Browser for specific sites
- "Write a script to track prices" → Shell (simple) or Claude Code (complex)
- "Set up a workflow to check prices daily" → Cron (simple schedule) or N8N (multi-step)
- "Deploy a new service" → Docker
- "Check system health" → Shell (df, free, systemctl, docker ps)
- "Build me a tool" → Claude Code
- "Check a GitHub repo" → gh CLI
- "Order something online" → Browser, but ALWAYS confirm with Trey before checkout

## Config Editing Rules
- JSON files: always lowercase true and false. Never Python True/False.
- Never use sed to edit JSON. Use python3 json module or openclaw config set.
- After any JSON edit, validate: cat ~/.openclaw/openclaw.json | python3 -m json.tool > /dev/null
- Config is schema-strict. Unknown keys block gateway startup. Don't guess key names.
- Before editing config, check the schema: openclaw config get <key> to see current values first.
- Backup exists at openclaw.json.bak. Restore with: cp ~/.openclaw/openclaw.json.bak ~/.openclaw/openclaw.json

## Editing JSON Safely
- NEVER use sed to edit JSON files. It doesn't understand JSON structure.
- Use python3 for modifications. Always use lowercase true/false in the output.
- Or use openclaw config set when possible — it validates before writing.
- When writing a complete new config, use cat > file.json << 'EOF' with full content.

## Gateway Restart Warning
- Gateway restart kills your current session. You will stop responding mid-message.
- NEVER restart the gateway as part of a multi-step task. Finish ALL work first, then restart as the final step.
- If a config change requires restart, tell Trey: "I need to restart the gateway to apply this. I'll go silent for a moment and come back." Then restart.
- After restart, you lose all context. Check memory files to recover what you were doing.

## File Ownership
- Never run sudo with npm, npx, or openclaw commands. Run those as wire_back.
- sudo creates root-owned files that break device identity and pairing.
- If pairing breaks: sudo chown -R wire_back:wire_back ~/.openclaw/ ~/.cache/

## Device Pairing
- If CLI says "pairing required": openclaw devices list then openclaw devices approve <id>
- Loopback connections should auto-approve. If stuck, fix file ownership first.

## Updates
- Before updating OpenClaw, back up config: cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.pre-update
- Run updates as wire_back, never sudo: openclaw update
- After update run: openclaw doctor --fix

## Skill Installation Protocol

ClawHub has had major security incidents. Over 1,400 malicious skills were found in 2026. Treat every skill as untrusted code.

### Before installing ANY skill, ask:
- Can I already do this with Playwright, Docker, Claude Code, or shell commands?
- If yes, DON'T install the skill. Use native tools.

### If a skill is genuinely needed:
1. Report to Trey: name, author, download count, last update, VirusTotal status
2. Check GitHub repo: stars, commits, author history
3. Red flags — DO NOT INSTALL if:
 - Author account less than 3 months old
 - Download count under 1,000
 - No VirusTotal report or flagged results
 - Requests permissions it shouldn't need
 - curl piping to bash from unknown URLs
 - Base64 encoded strings in source
4. Trey must explicitly approve before install

### Currently installed skills:
- security-auditor ✅ (verified)
- github ✅ (verified, needs gh auth)
