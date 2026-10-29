# ESPRIEAETHER Recovery Guide — Parrot Linux

## After fresh install / format:

### 1. Install base packages
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

### 4. Configure .env
```bash
cp .env.example .env
# Edit .env with your actual tokens:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - OKX API keys
# - GitHub token
# - Other service keys
nano .env
```

### 5. Start services
```bash
# Linux/Mac:
chmod +x AetherStartup.ps1 start_all_services.bat
# Use: python3 src/sunna_api.py &
#      python3 src/web_interface.py &
#      python3 src/cloud_desktop_agent.py &
```

### 6. Obsidian sync
```bash
python3 scripts/sync_to_obsidian.py
```

## Important notes:
- DO NOT email .env file (contains secrets)
- GitHub repo has all code: https://github.com/007aether/esprieaether
- Telegram bot token needs regeneration from @BotFather
- OKX keys need to be re-entered manually
