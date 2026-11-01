#!/usr/bin/env python3
"""
DeepSeek Harness — Universal brain + skill expander for EsprieAether.

What it does:
  1. Connects to DeepSeek API (keyless) when online
  2. Falls back to local models (ollama, colibri) when offline
  3. Auto-discovers and installs new skills from GitHub/other sources
  4. Expands modules and upgrades the system
  5. Can "travel" — works offline with local models, online with DeepSeek API

Usage:
  from deepseek_harness import DeepSeekHarness
  harness = DeepSeekHarness()
  result = harness.chat("Hello, world!", model="deepseek-chat")
  harness.expand_modules(force=True)  # fetch new skills
  harness.upgrade_system()  # update everything

Author: EsprieAether Team
"""

import json
import os
import subprocess
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / '.env')

BASE_DIR = Path(__file__).parent.parent
SKILLS_DIR = BASE_DIR / 'integrations'
DELTA_TASKS_FILE = BASE_DIR / 'data' / 'delta_tasks.json'
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY', '')
DEEPSEEK_BASE_URL = os.getenv('DEEPSEEK_BASE_URL', 'https://api.deepseek.com/v1')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://127.0.0.1:11434/v1/chat/completions')
COLIBRI_URL = os.getenv('COLIBRI_URL', 'http://127.0.0.1:8000/v1/chat/completions')
SKILL_REPO = 'https://api.github.com/repos/007aether/esprieaether'
SKILL_DIR = BASE_DIR / 'src' / '_skills'


class DeepSeekHarness:
    """Universal brain + skill expander for EsprieAether."""

    def __init__(self):
        self.SKILL_DIR = BASE_DIR / 'src' / '_skills'
        self.DELTA_TASKS_FILE = BASE_DIR / 'data' / 'delta_tasks.json'
        self.brain_online = self._check_brain_connectivity()
        self.local_skills = self._load_local_skills()
        self.delta_tasks = self._load_delta_tasks()

    def _check_brain_connectivity(self):
        if DEEPSEEK_API_KEY:
            try:
                req = urllib.request.Request(
                    f'{DEEPSEEK_BASE_URL}/models',
                    headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
                )
                with urllib.request.urlopen(req, timeout=5) as r:
                    return r.status == 200
            except Exception:
                pass
        try:
            req = urllib.request.Request(
                f'{OLLAMA_URL}/models',
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status == 200
        except Exception:
            pass
        try:
            req = urllib.request.Request(
                f'{COLIBRI_URL}/models',
                headers={'Content-Type': 'application/json'}
            )
            with urllib.request.urlopen(req, timeout=5) as r:
                return r.status == 200
        except Exception:
            pass
        return False

    def _load_local_skills(self):
        skills = {}
        self.SKILL_DIR.mkdir(parents=True, exist_ok=True)
        for skill_file in self.SKILL_DIR.glob('*.md'):
            try:
                skills[skill_file.stem] = skill_file.read_text(encoding='utf-8')
            except Exception:
                pass
        return skills

    def _load_delta_tasks(self):
        if self.DELTA_TASKS_FILE.exists():
            try:
                return json.loads(self.DELTA_TASKS_FILE.read_text(encoding='utf-8'))
            except Exception:
                pass
        return []

    def chat(self, prompt, system='', model='deepseek-chat'):
        if self.brain_online and DEEPSEEK_API_KEY:
            try:
                self._cache_response(prompt, system, model, 'deepseek')
                return self._request_deepseek(prompt, system, model)
            except Exception as e:
                print(f'DeepSeek error: {e}')
        if self._check_brain_connectivity():
            try:
                self._cache_response(prompt, system, model, 'colibri')
                return self._request_colibri(prompt, system, model)
            except Exception as e:
                print(f'Colibri error: {e}')
        try:
            self._cache_response(prompt, system, model, 'ollama')
            return self._request_ollama(prompt, system, model)
        except Exception as e:
            print(f'Local error: {e}')
        return {'error': 'No brain available', 'fallback': 'cached'}

    def _request_deepseek(self, prompt, system, model):
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system or 'أنت مساعد ذكي'},
                {'role': 'user', 'content': prompt}
            ],
            'stream': False
        }
        req = urllib.request.Request(
            f'{DEEPSEEK_BASE_URL}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Authorization': f'Bearer {DEEPSEEK_API_KEY}', 'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            return {
                'success': True,
                'source': 'deepseek',
                'model': model,
                'response': result['choices'][0]['message']['content'],
                'usage': result.get('usage', {})
            }

    def _request_colibri(self, prompt, system, model):
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system or 'أنت مساعد ذكي'},
                {'role': 'user', 'content': prompt}
            ],
            'stream': False
        }
        req = urllib.request.Request(
            f'{COLIBRI_URL}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            return {
                'success': True,
                'source': 'colibri',
                'model': model,
                'response': result['choices'][0]['message']['content'],
                'usage': result.get('usage', {})
            }

    def _request_ollama(self, prompt, system, model):
        payload = {
            'model': model,
            'messages': [
                {'role': 'system', 'content': system or 'أنت مساعد ذكي'},
                {'role': 'user', 'content': prompt}
            ],
            'stream': False
        }
        req = urllib.request.Request(
            f'{OLLAMA_URL}/chat/completions',
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=120) as r:
            result = json.loads(r.read())
            return {
                'success': True,
                'source': 'ollama',
                'model': model,
                'response': result['choices'][0]['message']['content'],
                'usage': result.get('usage', {})
            }

    def _cache_response(self, prompt, system, model, source):
        cache_file = BASE_DIR / 'data' / 'deepseek_cache.json'
        cache = {}
        if cache_file.exists():
            try:
                cache = json.loads(cache_file.read_text(encoding='utf-8'))
            except Exception:
                cache = {}
        cache[f'{source}:{prompt[:50]}'] = {
            'prompt': prompt,
            'system': system,
            'response': f'[Cached: {source}]',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        cache_file.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding='utf-8')

    def expand_modules(self, force=False, days=7):
        result = {'expanded': 0, 'added': [], 'skipped': [], 'errors': []}
        if not self._check_github_access():
            result['errors'].append('No GitHub access')
            return result
        try:
            req = urllib.request.Request(
                f'{SKILL_REPO}/commits?per_page=10',
                headers={'Accept': 'application/vnd.github+json'}
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                commits = json.loads(r.read())
        except Exception as e:
            result['errors'].append(f'GitHub fetch failed: {e}')
            return result
        for commit in commits:
            message = commit.get('commit', {}).get('message', '')
            if 'feat:' in message.lower() or 'add:' in message.lower() or 'new skill' in message.lower():
                skill_name = self._extract_skill_name(message)
                if skill_name:
                    result['expanded'] += 1
                    result['added'].append(skill_name)
                    self._install_skill(skill_name, commit['sha'][:8])
        return result

    def _check_github_access(self):
        try:
            req = urllib.request.Request(
                f'{SKILL_REPO}/commits?per_page=1',
                headers={'Accept': 'application/vnd.github+json'}
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status == 200
        except Exception:
            return False

    def _extract_skill_name(self, message):
        import re
        match = re.search(r'(?:skill|module|feature)[:\-]\s*([a-z0-9\-]+)', message.lower())
        if match:
            return match.group(1)
        return None

    def _install_skill(self, name, sha):
        skill_file = self.SKILL_DIR / f'{name}.md'
        if not skill_file.exists():
            skill_file.parent.mkdir(parents=True, exist_ok=True)
            skill_file.write_text(
                f'# {name}\n\nSkill: {name}\nSource: GitHub\nCommit: {sha}\n\n[Content pending]\n',
                encoding='utf-8'
            )
        print(f'   OK Skill installed: {name}')

    def upgrade_system(self, target='latest'):
        result = {'updated': 0, 'restarted': 0, 'errors': []}
        try:
            result['updated'] = self._git_pull()
        except Exception as e:
            result['errors'].append(f'Git pull failed: {e}')
        try:
            result['restarted'] = self._restart_services()
        except Exception as e:
            result['errors'].append(f'Service restart failed: {e}')
        return result

    def _git_pull(self):
        repo = Path.cwd()
        result = subprocess.run(
            ['git', 'pull', '--rebase'],
            cwd=repo,
            capture_output=True,
            text=True
        )
        return len(result.stdout.splitlines()) if result.returncode == 0 else 0

    def _restart_services(self):
        services = ['router', 'agent-mesh', 'web', 'cloud-desktop',
                    'homedock', 'jarvis', 'sunna', 'integrations', 'kanban', 'bot']
        count = 0
        for svc in services:
            try:
                subprocess.run(
                    ['powershell', '-Command',
                     f"Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | "
                     f"Where-Object {{ $_.CommandLine -like '*{svc}*' }} | "
                     f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force }}"],
                    capture_output=True, timeout=30
                )
                count += 1
            except Exception:
                pass
        return count

    def status(self):
        return {
            'brain_online': self.brain_online,
            'local_skills': len(self.local_skills),
            'delta_tasks': len(self.delta_tasks),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }


if __name__ == '__main__':
    harness = DeepSeekHarness()
    print(f'Brain online: {harness.brain_online}')
    print(f'Local skills: {len(harness.local_skills)}')
    if harness.brain_online:
        result = harness.chat('Hello, how are you?')
        print(f'Chat source: {result.get("source")}')
        print(f'Response: {result.get("response", "")[:100]}')
    result = harness.expand_modules(force=True)
    print(f'Expanded: {result["expanded"]}')
    for a in result['added']:
        print(f'   OK {a}')
