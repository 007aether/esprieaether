# nightingale.py
"""
This module is designed to collect information about the environment or system status for an autonomous agent
in the EspireAether system. It adheres to guidelines for no secrets, no destructive operations, and no network calls.
All input is expected to be within the package's directory structure.

Module constants:
- INTERVAL_MIN: The number of minutes until the next data gathering.
- TAGS: List of tags associated with this module.

"""

import platform
import psutil
from datetime import datetime

# Module constants
INTERVAL_MIN = 5  # Data collection cycle interval in minutes
TAGS = ["sys_info", "environment_monitoring"]

class Nightingale:
    def __init__(self):
        """
        Initializes the Nightingale monitor with current system and hardware information.
        """
        self.system_info = self.get_system_data()
        self.human_info = self.get_human_data()

    @staticmethod
    def get_system_data() -> dict:
        """
        Collects system-specific data (like CPU, memory, and disk usage).
        """
        system_info = {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "username": platform.username(),
            "platform": platform.platform()
        }
        return system_info

    @staticmethod
    def get_human_data() -> dict:
        """
        Collects user-specific data (like uptime, processes, and system status).
        """
        human_info = {
            "uptime": datetime.now() - datetime.fromtimestamp(psutil.boot_time()),
            "running_processes": len(psutil.pids())
        }
        return human_info

    def gather(self) -> dict:
        """
        Gatheres data about system and environment.
        Returns a dict with system and human data for monitoring purposes.
        """
        return {"system": self.system_info, "human": self.human_info}

    def main(self) -> None:
        """
        Main function to run the gather function in a loop every INTERVAL_MIN minutes.
        """
        while True:
            current_data = self.gather()
            print(f"Current data at {datetime.now()}:\n{current_data}")
            import time
            time.sleep(INTERVAL_MIN * 60)

# Entry point for the module
if __name__ == "__main__":
    monitor = Nightingale()
    monitor.main()
