# src/thinking_agent/runner.py
"""
Simple runner to execute ThinkingAgent.run_once() manually.
Run:
    python -m src.thinking_agent.runner
"""
from src.thinking_agent.agent import ThinkingAgent
from src.db_manager import DBManager
import json

def main():
    db = DBManager()
    agent = ThinkingAgent(db=db)
    result = agent.run_once()
    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
