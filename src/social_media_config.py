#!/usr/bin/env python3
"""
ESPRIEAETHER — Social Media Configuration
Platforms: Facebook, Instagram, YouTube, TikTok, Twitter/X
Brand: esprieaether
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SOCIAL_CONFIG = {
    "brand": "esprieaether",
    "email": "007aether@gmail.com",
    "platforms": {
        "youtube": {
            "channel_id": os.getenv("YT_CHANNEL_ID", ""),
            "channel_url": "https://youtube.com/@esprieaether",
            "enabled": False,
        },
        "facebook": {
            "page_id": os.getenv("FB_PAGE_ID", ""),
            "page_url": os.getenv("FB_PAGE_URL", ""),
            "access_token": os.getenv("FB_ACCESS_TOKEN", ""),
            "enabled": False,
        },
        "instagram": {
            "username": os.getenv("IG_USERNAME", "esprieaether"),
            "password": os.getenv("IG_PASSWORD", ""),
            "access_token": os.getenv("IG_ACCESS_TOKEN", ""),
            "enabled": False,
        },
        "tiktok": {
            "username": os.getenv("TT_USERNAME", "esprieaether"),
            "access_token": os.getenv("TT_ACCESS_TOKEN", ""),
            "enabled": False,
        },
        "twitter": {
            "username": os.getenv("X_USERNAME", "esprieaether"),
            "access_token": os.getenv("X_ACCESS_TOKEN", ""),
            "enabled": False,
        },
    },
}

def get_platform(platform: str) -> dict:
    return SOCIAL_CONFIG["platforms"].get(platform, {})

def enable_platform(platform: str, **kwargs):
    if platform in SOCIAL_CONFIG["platforms"]:
        SOCIAL_CONFIG["platforms"][platform].update(kwargs)
        SOCIAL_CONFIG["platforms"][platform]["enabled"] = True

def get_status() -> dict:
    return {
        "brand": SOCIAL_CONFIG["brand"],
        "platforms": {
            k: {"enabled": v["enabled"], "configured": bool(v.get("access_token") or v.get("channel_id") or v.get("page_id"))}
            for k, v in SOCIAL_CONFIG["platforms"].items()
        },
    }
