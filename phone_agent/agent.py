"""Main PhoneAgent class for orchestrating phone automation."""

import json
import traceback
from dataclasses import dataclass
from typing import Any, Callable

from phone_agent.actions import ActionHandler
from phone_agent.actions.handler import do, finish, parse_action
from phone_agent.adb import get_current_app, get_screenshot
from phone_agent.config import get_messages, get_system_prompt
from phone_agent.model import ModelClient, ModelConfig
from phone_agent.model.client import MessageBuilder


@dataclass
class AgentConfig:
    """Configuration for the PhoneAgent."""

    max_steps: int = 100
    device_id: str | None = None
    lang: str = "cn"
    system_prompt: str | None = None
    verbose: bool = True

    def __post_init__(self):
        if self.system_prompt is None:
            self.system_prompt = get_system_prompt(self.lang)


@dataclass
class StepResult:
    """Result of a single agent step."""

    success: bool
    finished: bool
    action: dict[str, Any] | None
    thinking: str
    message: str | None = None


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.

    Args:
        model_config: Configuration for the AI model.
        agent_config: Configuration for the agent behavior.
        confirmation_callback: Optional callback for sensitive action confirmation.
        takeover_callback: Optional callback for takeover requests.

    Example:
        >>> from phone_agent import PhoneAgent
        >>> from phone_agent.model import ModelConfig
        >>>
        >>> model_config = ModelConfig(base_url="http://localhost:8000/v1")
        >>> agent = PhoneAgent(model_config)
        >>> agent.run("Open WeChat and send a message to John")
    """

    # Loop detection settings
    MAX_SAME_ACTION_COUNT = 3  # Max times to repeat same action before breaking loop

    def __init__(
        self,
        model_config: ModelConfig | None = None,
        agent_config: AgentConfig | None = None,
        confirmation_callback: Callable[[str], bool] | None = None,
        takeover_callback: Callable[[str], None] | None = None,
    ):
        self.model_config = model_config or ModelConfig()
        self.agent_config = agent_config or AgentConfig()

        self.model_client = ModelClient(self.model_config)
        self.action_handler = ActionHandler(
            device_id=self.agent_config.device_id,
            confirmation_callback=confirmation_callback,
            takeover_callback=takeover_callback,
        )

        self._context: list[dict[str, Any]] = []
        self._step_count = 0
        self._last_actions: list[str] = []  # Track recent actions for loop detection

    def run(self, task: str) -> str:
        """
        Run the agent to complete a task.

        Args:
            task: Natural language description of the task.

        Returns:
            Final message from the agent.
        """
        self._context = []
        self._step_count = 0

        # First step with user prompt
        result = self._execute_step(task, is_first=True)

        if result.finished:
            return result.message or "Task completed"

        # Continue until finished or max steps reached
        while self._step_count < self.agent_config.max_steps:
            result = self._execute_step(is_first=False)

            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """
        Execute a single step of the agent.

        Useful for manual control or debugging.

        Args:
            task: Task description (only needed for first step).

        Returns:
            StepResult with step details.
        """
        is_first = len(self._context) == 0

        if is_first and not task:
            raise ValueError("Task is required for the first step")

        return self._execute_step(task, is_first)

    def reset(self) -> None:
        """Reset the agent state for a new task."""
        self._context = []
        self._step_count = 0
        self._last_actions = []

    def _get_action_signature(self, action: dict[str, Any]) -> str:
        """Get a signature string for an action to detect duplicates."""
        action_type = action.get("action", "")
        element = action.get("element", [])
        return f"{action_type}:{element}"

    def _is_loop_detected(self, action: dict[str, Any]) -> bool:
        """Check if we're stuck in a loop executing the same action."""
        sig = self._get_action_signature(action)
        self._last_actions.append(sig)

        # Keep only recent actions
        if len(self._last_actions) > self.MAX_SAME_ACTION_COUNT + 1:
            self._last_actions = self._last_actions[-self.MAX_SAME_ACTION_COUNT - 1:]

        # Check if last N actions are the same
        if len(self._last_actions) >= self.MAX_SAME_ACTION_COUNT:
            recent = self._last_actions[-self.MAX_SAME_ACTION_COUNT:]
            if len(set(recent)) == 1:
                print(f"[Agent] ⚠️ Loop detected! Same action repeated {self.MAX_SAME_ACTION_COUNT} times: {sig}")
                return True

        return False

    def _break_loop(self, screenshot_height: int) -> dict[str, Any]:
        """Create an action to break out of a loop (scroll down)."""
        print("[Agent] Breaking loop by scrolling down...")
        self._last_actions = []  # Reset action history

        # Scroll down to see new content
        return do(
            action="Swipe",
            startPoint=[540, int(screenshot_height * 0.7)],
            endPoint=[540, int(screenshot_height * 0.3)],
            duration="500ms"
        )

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1
        print(f"\n[Agent] ===== Step {self._step_count} =====")

        # Capture current screen state
        print("[Agent] Capturing screenshot...")
        screenshot = get_screenshot(self.agent_config.device_id)
        print(f"[Agent] Screenshot: {screenshot.width}x{screenshot.height}, sensitive={screenshot.is_sensitive}")

        print("[Agent] Getting current app...")
        current_app = get_current_app(self.agent_config.device_id)
        print(f"[Agent] Current app: {current_app}")

        # Build messages
        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )

            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"{user_prompt}\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )
        else:
            screen_info = MessageBuilder.build_screen_info(current_app)
            text_content = f"** Screen Info **\n\n{screen_info}"

            self._context.append(
                MessageBuilder.create_user_message(
                    text=text_content, image_base64=screenshot.base64_data
                )
            )

        # Get model response
        try:
            print("[Agent] Requesting model response...")
            response = self.model_client.request(self._context)
            print(f"[Agent] Model response received")
        except Exception as e:
            print(f"[Agent] Model request failed: {e}")
            if self.agent_config.verbose:
                traceback.print_exc()
            return StepResult(
                success=False,
                finished=True,
                action=None,
                thinking="",
                message=f"Model error: {e}",
            )

        # Parse action from response
        try:
            action = parse_action(response.action)
        except ValueError as e:
            if self.agent_config.verbose:
                print(f"\n⚠️ Action parse error: {e}")
                print(f"Raw action: {response.action}")
            # Don't finish on parse error, create a Wait action to retry
            action = do(action="Wait", duration="2 seconds")

        # Loop detection - check if we're repeating the same action
        if self._is_loop_detected(action):
            action = self._break_loop(screenshot.height)

        if self.agent_config.verbose:
            # Print thinking process
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "=" * 50)
            print(f"💭 {msgs['thinking']}:")
            print("-" * 50)
            print(response.thinking)
            print("-" * 50)
            print(f"🎯 {msgs['action']}:")
            print(json.dumps(action, ensure_ascii=False, indent=2))
            print("=" * 50 + "\n")

        # Remove image from context to save space
        self._context[-1] = MessageBuilder.remove_images_from_message(self._context[-1])

        # Execute action
        try:
            print(f"[Agent] Executing action: {action.get('action', 'unknown')}")
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
            print(f"[Agent] Action result: success={result.success}, should_finish={result.should_finish}")
        except Exception as e:
            print(f"[Agent] Action execution failed: {e}")
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )

        # Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # Check if finished
        finished = action.get("_metadata") == "finish" or result.should_finish

        if finished and self.agent_config.verbose:
            msgs = get_messages(self.agent_config.lang)
            print("\n" + "🎉 " + "=" * 48)
            print(
                f"✅ {msgs['task_completed']}: {result.message or action.get('message', msgs['done'])}"
            )
            print("=" * 50 + "\n")

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get the current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get the current step count."""
        return self._step_count
