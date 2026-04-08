# Big Clank Long-Term Memory

## About Trey
- Located in Mesa/Gilbert, Arizona (MST, no DST)
- Prefers direct, short, no-BS responses
- Interests: bass fishing, Rust, Minecraft, 3D printing (CR-10), bin stores
- Has a brother who runs Gerald (another OpenClaw bot)

## Infrastructure
- This PC: Intel i7-9700, 64GB RAM, dead GPU, Ubuntu Server 24.04
- Network: isolated behind TP-Link ER605 on 192.168.50.x subnet
- API Provider: OpenRouter
- Channel: Telegram
- Sister bot: Clanker (runs on Hostinger VPS)
- Tailscale: Installed and running

## Installed Software
- Ubuntu Server 24.04 LTS
- Node.js
- OpenClaw
- Chromium (system)
- N8N (Docker, port 5678)
- Claude Code (v2.1.92)
- gh CLI (GitHub)

## Storage
- /mnt/archive (1TB Seagate HDD, ext4)
- /mnt/workspace (Samsung SSD 870, ext4)
- Archive structure: memory/, transcripts/, backups/

## Cron Jobs
- Weekly Sun 4am: Memory archive to /mnt/archive/memory
- Daily 3am: Config backup to /mnt/archive/backups

## Installed Skills
- security-auditor (verified)
- github (verified, needs gh auth)

## Setup Complete
All pending setup items completed on 2026-04-05.

## Lessons Learned
- ClawHub security incidents: 1,400+ malicious skills found in 2026
- Never install skills that duplicate native tools
- Always verify skills before installing

## Active Projects
(Track ongoing work here)
