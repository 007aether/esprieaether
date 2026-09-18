#!/usr/bin/env python3
"""
ESPRIEAETHER DASHBOARD - Web interface
"""

import streamlit as st
import sqlite3
import os
import pandas as pd
from datetime import datetime

DB = os.path.expanduser("~/ESPRIEAETHER/data/esprieaether.db")

st.set_page_config(page_title="ESPRIEAETHER", layout="wide", page_icon="🛡️")

# Dark theme
st.markdown("""
<style>
    .stApp { background-color: #000011; }
    h1, h2, h3 { color: #00ffcc !important; }
    .robot-card {
        background: linear-gradient(135deg, #001133, #002244);
        border: 1px solid #00ffcc33;
        border-radius: 8px;
        padding: 10px;
        margin: 5px 0;
    }
</style>
""", unsafe_allow_html=True)

st.title("🛡️ ESPRIEAETHER — Control Center")
st.caption("Sovereign Local AI | 100% Private | Uncensored | Free")

# Sidebar
with st.sidebar:
    st.header("🎮 Navigation")
    page = st.radio("Go to:", [
        "🏠 Home",
        "🤖 Robots (50)",
        "📋 Kanban",
        "🧬 Evolution",
        "🔒 Security",
        "📰 News",
        "🪂 Airdrops",
        "💻 GitHub Scans",
    ])

# ============ HOME ============
if page == "🏠 Home":
    st.header("🏠 Dashboard")
    
    col1, col2, col3, col4 = st.columns(4)
    
    conn = sqlite3.connect(DB)
    
    # Stats
    cursor = conn.execute("SELECT COUNT(*) FROM robots")
    col1.metric("🤖 Robots", cursor.fetchone()[0])
    
    cursor = conn.execute("SELECT COUNT(*) FROM tasks")
    col2.metric("📋 Tasks", cursor.fetchone()[0])
    
    cursor = conn.execute("SELECT COUNT(*) FROM evolution_log")
    col3.metric("🧬 Cycles", cursor.fetchone()[0])
    
    cursor = conn.execute("SELECT COUNT(*) FROM security_findings")
    col4.metric("🔒 Findings", cursor.fetchone()[0])
    
    conn.close()
    
    st.divider()
    st.markdown("### 🎯 ESPRIEAETHER Features")
    st.markdown("""
    - ✅ **50 Robots** across 7 organ systems
    - ✅ **Super Kanban** task orchestration
    - ✅ **Cloud Code** AI coding
    - ✅ **Self-Evolution** engine
    - ✅ **Security Scanner**
    - ✅ **GitHub / News / Airdrop scanners**
    - ✅ **100% Local** (no cloud)
    """)

# ============ ROBOTS ============
elif page == "🤖 Robots (50)":
    st.header("🤖 Robots System")
    
    conn = sqlite3.connect(DB)
    cursor = conn.execute("SELECT system, COUNT(*) FROM robots GROUP BY system")
    systems = cursor.fetchall()
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Robots", sum(s[1] for s in systems))
    col2.metric("Organ Systems", len(systems))
    cursor = conn.execute("SELECT COUNT(*) FROM robots WHERE status='active'")
    col3.metric("Active", cursor.fetchone()[0])
    
    st.divider()
    
    for system, count in systems:
        with st.expander(f"📂 {system.upper()} ({count})"):
            cursor = conn.execute('''
                SELECT id, name, role, status FROM robots WHERE system = ?
            ''', (system,))
            robots = cursor.fetchall()
            
            df = pd.DataFrame(robots, columns=["ID", "Name", "Role", "Status"])
            st.dataframe(df, use_container_width=True, hide_index=True)
    
    conn.close()

# ============ KANBAN ============
elif page == "📋 Kanban":
    st.header("📋 Super Kanban")
    
    conn = sqlite3.connect(DB)
    
    col1, col2, col3 = st.columns(3)
    
    for i, status in enumerate(['todo', 'doing', 'done']):
        cursor = conn.execute('''
            SELECT id, title, priority FROM tasks WHERE status = ?
        ''', (status,))
        tasks = cursor.fetchall()
        
        with [col1, col2, col3][i]:
            st.markdown(f"### {status.upper()} ({len(tasks)})")
            for t in tasks:
                icon = {"critical": "🔥", "high": "⚡", "medium": "•", "low": "·"}.get(t[2], "•")
                st.markdown(f"{icon} **[{t[0]}]** {t[1]}")
    
    conn.close()

# ============ EVOLUTION ============
elif page == "🧬 Evolution":
    st.header("🧬 Self-Evolution Cycles")
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT cycle, issues_found, improvements, timestamp FROM evolution_log ORDER BY cycle DESC", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.line_chart(df.set_index('cycle')['issues_found'])
    else:
        st.info("No cycles yet.")

# ============ SECURITY ============
elif page == "🔒 Security":
    st.header("🔒 Security Findings")
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT file, line, issue_type, severity FROM security_findings ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.success("✅ No security findings!")

# ============ NEWS ============
elif page == "📰 News":
    st.header("📰 Latest News")
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT source, title, link FROM news ORDER BY timestamp DESC LIMIT 30", conn)
    conn.close()
    
    if not df.empty:
        for _, row in df.iterrows():
            st.markdown(f"**[{row['source']}]** [{row['title']}]({row['link']})")
    else:
        st.info("No news yet. Run `python3 scanners/news_scanner.py`")

# ============ AIRDROPS ============
elif page == "🪂 Airdrops":
    st.header("🪂 Airdrops")
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT name, status, potential_value FROM airdrops ORDER BY timestamp DESC LIMIT 50", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No airdrops yet.")

# ============ GITHUB ============
elif page == "💻 GitHub Scans":
    st.header("💻 GitHub Scans")
    
    conn = sqlite3.connect(DB)
    df = pd.read_sql("SELECT repo_name, stars, language, url FROM github_scans ORDER BY stars DESC LIMIT 30", conn)
    conn.close()
    
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No scans yet.")

# Footer
st.divider()
st.caption("⚡ ESPRIEAETHER v2.0 | Fusion Edition | Intelligence is Local")
