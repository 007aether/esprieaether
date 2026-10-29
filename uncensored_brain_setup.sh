#!/usr/bin/env bash
# Install and configure uncensored local brain for ESPRIEAETHER
# Model: Qwen2.5-Coder-7B-Instruct (uncensored, coding-focused)
set -e

echo "=== ESPRIEAETHER Uncensored Local Brain Setup ==="

# 1. Install Ollama if not present
if ! command -v ollama >/dev/null 2>&1; then
    echo "[1/5] Installing Ollama..."
    curl -fsSL https://ollama.ai/install.sh | bash
else
    echo "[1/5] Ollama already installed"
fi

# 2. Pull uncensored model
echo "[2/5] Pulling uncensored brain model..."
ollama pull qwen2.5-coder:7b-instruct

# 3. Create Ollama service
echo "[3/5] Configuring Ollama service..."
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/ollama.service << 'OLLAMA'
[Unit]
Description=Ollama Service
After=network.target

[Service]
ExecStart=/usr/local/bin/ollama serve
Restart=always
Environment=HOME=%h
Environment=PATH=/usr/local/bin:/usr/bin:/bin
Environment=OLLAMA_MODELS=/root/.ollama/models

[Install]
WantedBy=default.target
OLLAMA

systemctl --user enable ollama
systemctl --user start ollama

# 4. Configure ESPRIEAETHER to use local brain
echo "[4/5] Configuring ESPRIEAETHER .env..."
if [ -f .env ]; then
    if ! grep -q "BRAIN_MODEL" .env; then
        echo "" >> .env
        echo "# Uncensored Local Brain" >> .env
        echo "BRAIN_MODEL=qwen2.5-coder:7b-instruct" >> .env
        echo "BRAIN_HOST=http://localhost:11434" >> .env
        echo "BRAIN_TYPE=ollama" >> .env
        echo "BRAIN_LOCAL=true" >> .env
    fi
fi

# 5. Test brain
echo "[5/5] Testing brain..."
sleep 3
ollama list | grep qwen2.5-coder && echo "[ok] Brain ready" || echo "[!] Brain not ready"

echo "=== Uncensored Brain Setup Complete ==="
echo "Model: qwen2.5-coder:7b-instruct"
echo "Service: ollama (systemd user)"
echo "Config: .env updated"
