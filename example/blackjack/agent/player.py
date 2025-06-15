from abc import ABC, abstractmethod
from typing import Optional, List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.tool import ToolCollection, Terminate

from example.blackjack.prompt.player import SYSTEM_PROMPT, NEXT_STEP_PROMPT


class PlayerAgent(ToolCallAgent):
    name: str = Field(..., description="Unique name for this player agent")
    description: str = "AI player for blackjack game, follow the instruction given by host, and decide what to do."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        Terminate()
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 50
