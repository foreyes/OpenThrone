from typing import Any, Dict, Optional

from app.tool import BaseTool
from app.agent_manager import AgentManager


class MsgToAgent(BaseTool):
    """Add a tool to communicate with other agent."""

    name: str = "msg_to_agent"
    description: str = "Use this tool to communicate with other agent. Agent list: {agent_list}"
    parameters: str = {
        "type": "object",
        "properties": {
            "your_name": {
                "type": "string",
                "description": "Your name, the agent who sends the message.",
            },
            "agent_name": {
                "type": "string",
                "description": "The name of the agent you want to communicate with.",
            },
            "message": {
                "type": "string",
                "description": "The message you want to send to other agent.",
            }
        },
        "required": ["agent_name", "message"],
    }

    def to_param(self) -> Dict:
        params = super().to_param()
        params["function"]["description"] = self.description.format(agent_list=AgentManager.list_agents())
        return params

    async def execute(self, your_name: str, agent_name: str, message: str) -> str:
        """Send a message to another agent and return the response."""
        agent = AgentManager.get_agent(agent_name)
        if not agent:
            return f"Agent {agent_name} not found."

        request: str = f"Agent {your_name} send message for you, and you have to response that: {message}\n"
        response = await agent.run(request)

        return f"Agent {agent_name} response: {response}"

