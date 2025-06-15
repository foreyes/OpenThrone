from typing import Dict, List, Optional
from app.agent.base import BaseAgent

class AgentManager:
    """全局的 Agent 注册与检索管理器"""

    # 存储 name->agent 实例的映射
    _agents: Dict[str, BaseAgent] = {}

    @classmethod
    def register_agent(cls, agent: BaseAgent) -> None:
        cls._agents[agent.name] = agent

    @classmethod
    def get_agent(cls, name: str) -> Optional[BaseAgent]:
        return cls._agents.get(name)

    @classmethod
    def list_agents(cls) -> List[Dict[str, str]]:
        return [
            {"name": agent.name, "description": agent.description or ""}
            for agent in cls._agents.values()
        ]
