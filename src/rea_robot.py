#!/usr/bin/env python3
"""
⚡ EsprieAether - REA Robot (Reverse Engineering Agent)
Creates robots and analyzes systems using reverse engineering.
"""

import os
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys_path_needed = str(BASE_DIR / "src")
if sys_path_needed not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_path_needed)

logger = logging.getLogger("rea_robot")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

class REARobot:
    """روبوت الهندسة العكسية -Creates robots and analyzes systems"""
    
    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.log_file = self.data_dir / "rea_robot_log.json"
        self.history = self._load_history()
    
    def _load_history(self) -> dict:
        if self.log_file.exists():
            try:
                return json.loads(self.log_file.read_text())
            except:
                return {"robots_created": [], "systems_analyzed": [], "last_run": None}
        return {"robots_created": [], "systems_analyzed": [], "last_run": None}
    
    def create_robot(self, name: str, role: str, capabilities: list):
        """يخلق روبوت جديد"""
        robot = {
            "name": name,
            "role": role,
            "capabilities": capabilities,
            "created_at": datetime.now().isoformat(),
            "status": "active"
        }
        
        self.history["robots_created"].append(robot)
        self._save()
        
        # Generate robot file
        self._generate_robot_file(name, role, capabilities)
        
        logger.info(f"✅ Robot '{name}' created successfully")
        return robot
    
    def _generate_robot_file(self, name: str, role: str, capabilities: list):
        """يولد ملف الروبوت"""
        content = f'''#!/usr/bin/env python3
"""
⚡ EsprieAether - {name}
{role}
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
sys_path_needed = str(BASE_DIR + "/src")
if sys_path_needed not in sys.path:
    sys.path.insert(0, sys_path_needed)

logger = logging.getLogger("{name}")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
)

class {name.capitalize()}:
    """{role}"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.log_file = self.data_dir / "{name}_log.json"
        self.history = self._load_history()
    
    def _load_history(self) -> dict:
        if self.log_file.exists():
            try:
                return json.loads(self.log_file.read_text())
            except:
                return {{"created": [], "tasks": [], "last_run": None}}
        return {{"created": [], "tasks": [], "last_run": None}}
    
    def _save(self):
        self.history["last_run"] = datetime.now().isoformat()
        self.log_file.write_text(json.dumps(self.history, indent=2, ensure_ascii=False))
    
    def run(self):
        """Define robot behavior here"""
        logger.info("Robot started")
        # To be defined
        return {{"status": "ok", "robot": "{name}"}}
'''
        robot_file = self.data_dir / f"robot_{name.lower().replace(' ', '_')}.py"
        robot_file.write_text(content)
        os.chmod(robot_file, 0o755)
        logger.info(f"📄 Robot file created: {robot_file}")
    
    def analyze_system(self, path: str, depth: int = 2) -> dict:
        """يحلل النظام"""
        result = {
            "path": path,
            "depth": depth,
            "files_found": 0,
            "functions_found": 0,
            "classes_found": 0,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            for root, dirs, files in os.walk(path):
                for f in files:
                    if f.endswith('.py'):
                        result["files_found"] += 1
                        filepath = os.path.join(root, f)
                        try:
                            with open(filepath, 'r', encoding='utf-8') as file:
                                content = file.read()
                                result["functions_found"] += len(re.findall(r'def\s+\w+', content))
                                result["classes_found"] += len(re.findall(r'class\s+\w+', content))
                        except:
                            pass
        except Exception as e:
            result["error"] = str(e)
        
        self.history["systems_analyzed"].append(result)
        self._save()
        
        return result
    
    def get_stats(self) -> dict:
        """إحصائيات"""
        return {
            "robots_created": len(self.history.get("robots_created", [])),
            "systems_analyzed": len(self.history.get("systems_analyzed", [])),
            "total_tasks": len(self.history.get("tasks", [])),
            "last_run": self.history.get("last_run"),
            "timestamp": datetime.now().isoformat()
        }
    
    def _save(self):
        self.history["last_run"] = datetime.now().isoformat()
        self.log_file.write_text(json.dumps(self.history, indent=2, ensure_ascii=False))

# Test
if __name__ == "__main__":
    robot = REARobot()
    print("🔧 REA Robot test...")
    
    # Create a robot
    robot.create_robot(
        name="analysis_bot",
        role="وكيل التحليل والتطوير الذاتي",
        capabilities=["analyze_code", "generate_robot", "self_improve", "github_integration"]
    )
    
    # Analyze system
    stats = robot.analyze_system("src", depth=2)
    print(f"System analysis: {stats['files_found']} files, {stats['functions_found']} functions")
    
    # Stats
    print(f"REA Robot stats: {json.dumps(robot.get_stats(), indent=2, ensure_ascii=False)}")
    print("✅ REA Robot test complete")
