from abc import ABC, abstractmethod
from typing import Optional, List

from pydantic import Field

from app.agent.toolcall import ToolCallAgent
from app.tool import ToolCollection, Terminate
from app.custom_tool import MsgToAgent

from example.blackjack.prompt.host import SYSTEM_PROMPT, NEXT_STEP_PROMPT


class HostAgent(ToolCallAgent):
    name: str = "game_host"
    description: str = "AI host for blackjack game, managing game state and player interactions."

    system_prompt: str = SYSTEM_PROMPT
    next_step_prompt: str = NEXT_STEP_PROMPT

    available_tools: ToolCollection = ToolCollection(
        MsgToAgent(), Terminate()
    )
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    max_steps: int = 50
