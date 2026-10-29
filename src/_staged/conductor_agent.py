# Module: autonomous_agent.py
# Description: This module contains the autonomous_agent class that collects data periodically.
#              The gather function collects data and returns it as a dictionary.
# Requirements: None, uses only standard library functions.

import threading
import time

class AutonomousAgent:
    """
    This class manages the autonomous operation of the agent in the EspireAether system.
    
    The gather method is responsible for collecting data periodically.
    """
    INTERVAL_MIN = 5
    TAGS = {
        "System": "AutonomousAgent"
    }

    def gather(self) -> dict:
        """
        Collects data and returns it as a dictionary.
        
        Returns:
            dict: A dictionary containing the collected data.
        """
        
        # Simulate data collection
        data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": 25.5,
            "status": "Active"
        }
        
        return data

# Global class instances
AUTO_AGENT = AutonomousAgent()

def main():
    """
    Main function to start the autonomous operation.
    
    Returns:
        int: Completion status (0 on success, 1 on failure).
    """
    while True:
        # Gather data
        data = AUTO_AGENT.gather()
        print(f"Data gathered: {data}")
        
        # Sleep until next interval
        time.sleep(AUTO_AGENT.INTERVAL_MIN * 60)
    
    return 0

if __name__ == "__main__":
    main()
