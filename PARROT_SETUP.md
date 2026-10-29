# ESPRIEAETHER on Parrot Linux — Setup Guide

## After fresh install:

### 1. Install dependencies
```bash
sudo apt update && sudo apt install -y git python3 python3-venv python3-pip curl wget tmux zsh
```

### 2. Clone project
```bash
git clone https://github.com/007aether/esprieaether.git
cd esprieaether
```

### 3. Setup Python venv
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4. Configure environment
```bash
cp .env.example .env
nano .env
# Fill in:
# - TELEGRAM_BOT_TOKEN (regenerate from @BotFather)
# - OKX_API_KEY, OKX_SECRET, OKX_PASSPHRASE
# - GITHUB_TOKEN
```

### 5. Start services
```bash
chmod +x start_services_parrot.sh
./start_services_parrot.sh
```

### 6. Sync Obsidian
```bash
python3 scripts/sync_to_obsidian.py
```

## Notes:
- Old Windows .ps1/.bat scripts replaced by start_services_parrot.sh
- Paths auto-adjusted to Linux format
- Telegram token needs regeneration
- OKX keys need re-entry
