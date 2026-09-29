"""وكيل أساسي"""
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger("agent")


class BaseAgent(ABC):
    def __init__(self, name, role):
        self.name = name
        self.role = role
    
    @abstractmethod
    def run(self, task: str, context: dict = None) -> dict:
        pass
    
    def log(self, msg):
        logger.info(f"[{self.name}] {msg}")
