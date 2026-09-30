#!/bin/bash
cd ~/AETHER_V8
source .venv/bin/activate
python src/airdrop_advanced.py >> logs/airdrop_$(date +%Y%m%d).log 2>&1
