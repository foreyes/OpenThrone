import argparse
import asyncio

from app.logger import logger
from app.agent_manager import AgentManager

from example.blackjack.agent import HostAgent, PlayerAgent


async def main():
    """Run blackjack example."""

    # Create agents
    host = HostAgent()
    alice = PlayerAgent(name="Alice")
    bob = PlayerAgent(name="Bob")

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
