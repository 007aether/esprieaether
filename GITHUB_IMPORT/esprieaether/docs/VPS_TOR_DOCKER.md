# VPS + SSH Tunnel + Tor + Docker — setup guide

This is the remaining infrastructure work for EsprieAether sovereign ops.
Each section is independent; do them in the order that suits you.

---

## 1. VPS + TotalAV VPN tunnel

**Goal:** exit the PC through a cheap VPS (public IP) so the PC's real IP is
never exposed, and so the trading bot / OKX calls / JARVIS swarm always
egress from one stable country.

### Buy
Any provider works (Hetzner ~€4/mo, Contabo ~€5/mo, Oracle free tier).
Pick **Ubuntu 24.04 LTS**, 2GB RAM, 1 vCPU.

### Harden (on the VPS, as root)
```bash
adduser aether
usermod -aG sudo aether
# key-only SSH
mkdir -p /home/aether/.ssh
# paste your Windows public key (from ~/.ssh/id_ed25519.pub) into:
#   /home/aether/.ssh/authorized_keys
sed -i 's/^#\?PasswordAuthentication.*/PasswordAuthentication no/' /etc/ssh/sshd_config
systemctl reload ssh
ufw allow 22/tcp
ufw enable
```

### Tunnel (PC → VPS)
On the PC, keep a reverse SOCKS proxy alive so all EsprieAether traffic
egresses from the VPS:
```bash
ssh -N -D 1080 -i ~/.ssh/id_ed25519 aether@VPS_IP
```
Then point every service at the SOCKS proxy, or wrap calls in
`proxychains4 -f proxychains.conf`.

Better: run the **whole stack inside the VPS** (see Docker below) and keep
the PC as the operator terminal only.

---

## 2. Tor (blocked by TotalAV VPN — workaround)

**Problem:** direct Tor + TotalAV VPN can't reach the consensus
(`we have 0/9094 microdescriptors`) and bridges.torproject.org is blocked
by the VPN's DNS.

**Fix A — disconnect TotalAV, then run Tor:**
```bash
# stop TotalAV VPN, then:
cd ~/AppData/Local/Temp/tor2
./tor/tor.exe -f torrc
# wait for: Bootstrapped 100%
curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

**Fix B — Tor through the VPS (recommended):** run Tor *on the VPS*, tunnel
to it over SSH:
```bash
# on VPS:  apt install tor
# on PC:   ssh -N -L 9050:127.0.0.1:9050 aether@VPS_IP
# then:    curl --socks5 127.0.0.1:9050 https://check.torproject.org/api/ip
```

**Fix C — bridges fetched OFF the VPN** (phone hotspot / different network):
```bash
curl -s https://bridges.torproject.org/bridges?transport=snowflake | grep ^snowflake
# paste the lines into torrc under "Bridge ..."
```

---

## 3. Docker

**Static binaries are already downloaded** to
`~/AppData/Local/Temp/docker/docker/` (docker 27.3.1, no WSL needed).

### Run the daemon (needs an elevated shell)
```powershell
# right-click → Run as Administrator
cd $env:LOCALAPPDATA\Temp\docker
.\docker\dockerd.exe -H npipe://./pipe/docker_engine --data-root .\data
# in a second admin shell:
.\docker\docker.exe version
```

### Containers to run (the whole stack, portable)
`docker-compose.yml` (already planned for the repo) will hold:
- `aether-router` (11435)
- `aether-orchestrator` (11436)
- `aether-web` (5000)
- `aether-cloud-desktop` (5001)
- `jarvis` (8000)
- `watchdog` (sidecar, restarts the rest)

Build once on the VPS, pull on the PC — same image, same behaviour.

---

## 4. OKX live switch (when funded)

```bash
# after the account has funds, run the bot live for one cycle:
BOT_DRY_RUN=0 python src/okx_trading_bot.py --once
# if that looks right, run it 24/7 (added to startup):
BOT_DRY_RUN=0 python src/okx_trading_bot.py
```
Caps: max 10% of equity per trade, stop after 2% daily loss.
