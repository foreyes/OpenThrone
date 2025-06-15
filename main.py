import argparse
import asyncio

from app.agent.toolcall import ToolCallAgent
from app.logger import logger


async def main():
    """Run basic ToolCallAgent with command line input."""

    agent = ToolCallAgent()
    try:
        # Use command line prompt if provided, otherwise ask for input
        prompt = input("Enter your prompt: ")
        if not prompt.strip():
            logger.warning("Empty prompt provided.")
            return

        logger.warning("Processing your request...")
        await agent.run(prompt)
        logger.info("Request processing completed.")
    except KeyboardInterrupt:
        logger.warning("Operation interrupted.")
    finally:
        # Ensure agent resources are cleaned up before exiting
        await agent.cleanup()
        logger.info("Exiting application.")


if __name__ == "__main__":
    asyncio.run(main())
