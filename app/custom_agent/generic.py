import json

from abc import ABC, abstractmethod
from typing import Optional, Tuple, List, Any

from pydantic import Field

from app.agent.react import ReActAgent
from app.llm import LLM
from app.logger import logger
from app.schema import AgentState, Memory
from app.schema import TOOL_CHOICE_TYPE, Message, ToolCall, ToolChoice
from app.tool import ToolCollection, Terminate

from app.custom_agent.prompt.generic import SELF_THINK_NEXT_HINT_PROMPT


class SimpleGenericAgent(ReActAgent):
    # Basic settings
    name: str = Field(..., description="Unique name for this agent")
    description: str = Field(..., description="Simple description of this agent")
    max_steps: int = 20

    # Tool settings
    available_tools: ToolCollection = Field(default_factory=lambda: ToolCollection(Terminate()), description="Collection of tools available to the agent")
    tool_choices: TOOL_CHOICE_TYPE = Field(ToolChoice.AUTO) # type: ignore
    special_tool_names: List[str] = Field(default_factory=lambda: [Terminate().name])

    # Agent settings
    system_prompt: Optional[str] = Field(None, description="System-level instruction prompt for the agent")
    think_next_hint_prompt: Optional[str] = Field(None, description="User prompt to guide the agent's next thought process")
    self_think_next_hint_prompt: Optional[str] = Field(SELF_THINK_NEXT_HINT_PROMPT, description="Assistant prompt to guide the agent's next thought process")
    act_hint_prompt: Optional[str] = Field(None, description="User prompt to guide the agent's actions")
    
    # Private attributes
    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    current_step: int = 0
    tool_calls: List[ToolCall] = Field(default_factory=list)
    _current_base64_image: Optional[str] = None


    async def think(self) -> Tuple[bool, str]:
        """Process current state and decide next action"""
        print(f"\n[{self.name}] ------- Think ------- \n", flush=True)

        messages = self.messages
        if self.think_next_hint_prompt:
            messages += Message.user_message(self.think_next_hint_prompt)
        if self.self_think_next_hint_prompt:
            messages += Message.assistant_message(self.self_think_next_hint_prompt)
        
        success, response = await self.handle_llm_ask_tool(
            messages=messages,
            system_msgs=(
                [Message.system_message(self.system_prompt)]
                if self.system_prompt
                else None
            ),
            tools=self.available_tools.to_params(),
            tool_choice=self.tool_choices,
        )
        if not success:
            return False, ""
        
        self.tool_calls = tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""
        
        try:
            # Handle no tool call branch
            if not tool_calls:
                if content:
                    self.memory.add_message(Message.assistant_message(content))
                    return True, content
                return False, ""
            
            # Handle tool call branch
            assistant_msg = (
                Message.from_tool_calls(content=content, tool_calls=self.tool_calls)
                if self.tool_calls
                else Message.assistant_message(content)
            )
            self.memory.add_message(assistant_msg)
        except Exception as e:
            logger.error(f"Error processing tool calls: {e}")
            raise e
        
        return True, content # Always need to act, is that right? 


    async def act(self) -> str:
        """Execute decided actions"""
        print(f"\n[{self.name}] ------- Act ------- \n", flush=True)

        results = []
        for command in self.tool_calls:
            # Reset base64_image for each tool call
            self._current_base64_image = None

            result = await self.execute_tool(command)

            logger.info(f"🎯 Tool '{command.function.name}' completed its mission! Result: {result}")

            # Add tool response to memory
            tool_msg = Message.tool_message(
                content=result,
                tool_call_id=command.id,
                name=command.function.name,
                base64_image=self._current_base64_image,
            )
            self.memory.add_message(tool_msg)
            results.append(result)
        
        messages = self.messages
        if self.act_hint_prompt:
            messages += Message.user_message(self.act_hint_prompt)

        if self.state != AgentState.FINISHED:
            # take action (not tool call), request to llm
            success, response = await self.handle_llm_ask(
                messages=messages,
                system_msgs=(
                    [Message.system_message(self.system_prompt)]
                    if self.system_prompt
                    else None
                ),
            )
            if not success:
                raise RuntimeError(f"❗️ {self.name} failed to get a response from the LLM")
            self.memory.add_message(Message.assistant_message(response))
            results.append(response)

        return "\n\n".join(results)


    async def handle_llm_ask_tool(self, **kwargs) -> Tuple[bool, str]:
        """Call LLM ask and handle exception."""
        try:
            response = await self.llm.ask_tool(**kwargs)
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False, ""
            raise
        
        # Common error handling
        if not response:
            raise RuntimeError("No response received from the LLM")

        # Tool error handling
        tool_calls = (
            response.tool_calls if response and response.tool_calls else []
        )
        content = response.content if response and response.content else ""

        if self.tool_choices == ToolChoice.NONE:
            if tool_calls:
                logger.warning(
                    f"🤔 Hmm, {self.name} tried to use tools when they weren't available!"
                )
            if content:
                self.memory.add_message(Message.assistant_message(content))
                return True, content
            return False, content
        
        if self.tool_choices == ToolChoice.REQUIRED and not tool_calls:
            raise RuntimeError(f"❗️ {self.name} was required to use a tool but didn't call any tools!")
        
        return True, response

    async def handle_llm_ask(self, **kwargs) -> Tuple[bool, str]:
        """Call LLM ask and handle exception."""
        try:
            response = await self.llm.ask(**kwargs)
        except ValueError:
            raise
        except Exception as e:
            # Check if this is a RetryError containing TokenLimitExceeded
            if hasattr(e, "__cause__") and isinstance(e.__cause__, TokenLimitExceeded):
                token_limit_error = e.__cause__
                logger.error(
                    f"🚨 Token limit error (from RetryError): {token_limit_error}"
                )
                self.memory.add_message(
                    Message.assistant_message(
                        f"Maximum token limit reached, cannot continue execution: {str(token_limit_error)}"
                    )
                )
                self.state = AgentState.FINISHED
                return False, ""
            raise
        
        # Common error handling
        if not response:
            raise RuntimeError("No response received from the LLM")
        
        return True, response
    
    async def execute_tool(self, command: ToolCall) -> str:
        """Execute a single tool call with robust error handling"""
        if not command or not command.function or not command.function.name:
            return "Error: Invalid command format"

        name = command.function.name
        if name not in self.available_tools.tool_map:
            return f"Error: Unknown tool '{name}'"

        try:
            # Parse arguments
            args = json.loads(command.function.arguments or "{}")

            # Execute the tool
            logger.info(f"🔧 Activating tool: '{name}'...")
            print(f"🔧 Activating tool: '{name}'...")
            result = await self.available_tools.execute(name=name, tool_input=args)

            # Handle special tools
            await self._handle_special_tool(name=name, result=result)

            # Check if result is a ToolResult with base64_image
            if hasattr(result, "base64_image") and result.base64_image:
                # Store the base64_image for later use in tool_message
                self._current_base64_image = result.base64_image

            # Format result for display (standard case)
            observation = (
                f"Observed output of cmd `{name}` executed:\n{str(result)}"
                if result
                else f"Cmd `{name}` completed with no output"
            )

            return observation
        except json.JSONDecodeError:
            error_msg = f"Error parsing arguments for {name}: Invalid JSON format"
            logger.error(
                f"📝 Oops! The arguments for '{name}' don't make sense - invalid JSON, arguments:{command.function.arguments}"
            )
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"⚠️ Tool '{name}' encountered a problem: {str(e)}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"
    
    async def _handle_special_tool(self, name: str, result: Any, **kwargs):
        """Handle special tool execution and state changes"""
        if not self._is_special_tool(name):
            return

        if self._should_finish_execution(name=name, result=result, **kwargs):
            # Set agent state to finished
            logger.info(f"🏁 Special tool '{name}' has completed the task!")
            self.state = AgentState.FINISHED
    
    @staticmethod
    def _should_finish_execution(**kwargs) -> bool:
        """Determine if tool execution should finish the agent"""
        return True
    
    def _is_special_tool(self, name: str) -> bool:
        """Check if tool name is in special tools list"""
        return name.lower() in [n.lower() for n in self.special_tool_names]
    
    async def cleanup(self):
        """Clean up resources used by the agent's tools."""
        logger.info(f"🧹 Cleaning up resources for agent '{self.name}'...")
        for tool_name, tool_instance in self.available_tools.tool_map.items():
            if hasattr(tool_instance, "cleanup") and asyncio.iscoroutinefunction(
                tool_instance.cleanup
            ):
                try:
                    logger.debug(f"🧼 Cleaning up tool: {tool_name}")
                    await tool_instance.cleanup()
                except Exception as e:
                    logger.error(
                        f"🚨 Error cleaning up tool '{tool_name}': {e}", exc_info=True
                    )
        logger.info(f"✨ Cleanup complete for agent '{self.name}'.")
    
    async def run(self, request: Optional[str] = None) -> str:
        """Run the agent with cleanup when done."""
        try:
            return await super().run(request)
        finally:
            await self.cleanup()