import argparse
import asyncio

from app.logger import logger
from app.agent_manager import AgentManager
from app.tool import ToolCollection, Terminate

from app.custom_agent import SimpleGenericAgent
from app.custom_tool import MsgToAgent


HOST_SYSTEM_PROMPT = """You are an AI agent designed to host the game of Blackjack. You are not goint to interact with user or human, you need to host the game alone and interact with other AI agents, don't ask human for anything, just do what you want/need to do.
Your role is to manage the game state, provide instructions, and ensure the game runs smoothly. You need to follow these guides:
1. Generate a suffled deck of cards at the start of the game.
2. When the game is running, list the remaining cards in the deck.
3. When the game is running, list the current player hands.
4. Host the game by telling the players what's going on, and ask them to take actions. (You have to tell them about the hands and the discarded cards, and ask them to take actions.)
5. When the game is over, summarize the results and declare the winner.
6. Game will be played as Bo5 without resuffle the deck, so you need to keep track of the scores.
"""

HOST_USER_THINK_HINT_PROMPT = """If you don't know what todo, think about that: based on the current game state, what is the next action?
If you think everthing is finished and want to quit the game, use `terminate` tool/function call.
"""

PLAYER_SYSTEM_PROMPT = """You are an AI agent designed to play the game of Blackjack.
Your role is to follow the instructions given by the game host, and decide what you do.
1. Analyze the current game state and decide your next action.
2. The game is Bo5 without reshuffling the deck, you need to remember what's going on.
3. If you want to take an action, just say it, and use `terminate` tool with status `success`.
"""

PLAYER_USER_THINK_HINT_PROMPT = """Think about that: based on the current game state, what is your next action?
You have to response with your thoughts and actions, and use the `terminate` tool with status `success` at the same time to finish your current work and response to the host.
If you are only informed of certain things without being asked to take any action, you need to provide feedback of 'understood' (regardless of whether you decide to call any tools).
You can only use `terminate` tool after or at the same time that you give out any response.
"""

async def main():
    """Run blackjack example."""

    # 考虑任务是否复杂到需要切分 Think 和 Act 阶段，如果不需要的话不用给 act_hint_prompt，给出 think_next_hint_prompt 或者 self_think_next_hint_prompt 即可
    host = SimpleGenericAgent(
        name="Host",
        description="AI host for blackjack game, managing game state and player interactions.",
        available_tools=ToolCollection(
            MsgToAgent(), Terminate()
        ),
        system_prompt=HOST_SYSTEM_PROMPT,
        user_think_hint_prompt=HOST_USER_THINK_HINT_PROMPT,
    )
    alice = SimpleGenericAgent(
        name="Alice",
        description="AI player for blackjack game, follow the instruction given by host, and decide what to do.",
        available_tools=ToolCollection(
            Terminate()
        ),
        system_prompt=PLAYER_SYSTEM_PROMPT,
        user_think_hint_prompt=PLAYER_USER_THINK_HINT_PROMPT,
    )
    bob = SimpleGenericAgent(
        name="Bob",
        description="AI player for blackjack game, follow the instruction given by host, and decide what to do.",
        available_tools=ToolCollection(
            Terminate()
        ),
        system_prompt=PLAYER_SYSTEM_PROMPT,
        user_think_hint_prompt=PLAYER_USER_THINK_HINT_PROMPT,
    )

    # Register agents with the global agent manager
    AgentManager.register_agent(host)
    AgentManager.register_agent(alice)
    AgentManager.register_agent(bob)

    # Start the host agent to manage the game
    try:
        # prompt = "Start hosting the game."
        prompt = "开始主持游戏，使用中文回答"
        await host.run(prompt)
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await host.cleanup()
        await alice.cleanup()
        await bob.cleanup()
        logger.info("Exiting application.")


if __name__ == "__main__":
    asyncio.run(main())
