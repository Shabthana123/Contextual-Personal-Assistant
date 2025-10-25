# src/thinking_agent/scheduler.py
import threading
from typing import Optional
from src.thinking_agent.agent import ThinkingAgent
import time

class ThinkingScheduler:
    """
    Lightweight scheduler to run ThinkingAgent periodically.
    Uses threading.Timer to schedule repeated runs.
    """
    def __init__(self, agent: Optional[ThinkingAgent] = None, interval_seconds: int = 3600):
        self.agent = agent if agent else ThinkingAgent()
        self.interval = int(interval_seconds)
        self._timer = None
        self._stopped = True

    def _job(self):
        try:
            summary = self.agent.run_once()
            print(f"[ThinkingAgent] Run summary: {summary.get('summary', summary)}")
        except Exception as e:
            print(f"[ThinkingAgent] Error: {e}")
        finally:
            if not self._stopped:
                self._timer = threading.Timer(self.interval, self._job)
                self._timer.daemon = True
                self._timer.start()

    def start(self, initial_delay: int = 1):
        if not self._stopped:
            return
        self._stopped = False
        self._timer = threading.Timer(initial_delay, self._job)
        self._timer.daemon = True
        self._timer.start()
        print(f"[ThinkingAgent] Scheduler started (interval {self.interval}s)")

    def stop(self):
        self._stopped = True
        if self._timer:
            self._timer.cancel()
            self._timer = None
        print("[ThinkingAgent] Scheduler stopped")
