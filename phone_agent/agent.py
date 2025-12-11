"""Main PhoneAgent class for orchestrating phone automation."""

import json
from dataclasses import dataclass, field
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
    max_repeat: int = 3  # Max times to repeat same action/error before recovery

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


@dataclass
class AgentState:
    """Internal state tracking for the agent."""

    history: list[str] = field(default_factory=list)  # Recent action signatures
    error_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0

    def record(self, signature: str) -> None:
        """Record an action signature."""
        self.history.append(signature)
        if len(self.history) > 10:
            self.history = self.history[-10:]

    def is_stuck(self, max_repeat: int) -> bool:
        """Check if repeating same action."""
        if len(self.history) < max_repeat:
            return False
        recent = self.history[-max_repeat:]
        return len(set(recent)) == 1

    def record_error(self, error: str) -> bool:
        """Record error, return True if same error repeated."""
        if error == self.last_error:
            self.error_count += 1
        else:
            self.error_count = 1
            self.last_error = error
        return self.error_count >= 3

    def reset_errors(self) -> None:
        """Reset error tracking on success."""
        self.error_count = 0
        self.last_error = ""

    def clear(self) -> None:
        """Clear all state."""
        self.history.clear()
        self.error_count = 0
        self.last_error = ""
        self.recovery_attempts = 0


class PhoneAgent:
    """
    AI-powered agent for automating Android phone interactions.

    The agent uses a vision-language model to understand screen content
    and decide on actions to complete user tasks.
    """

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

    def run(self, task: str) -> str:
        """Run the agent to complete a task."""
        self.reset()

        result = self._step(task, is_first=True)
        if result.finished:
            return result.message or "Task completed"

        while self._step_count < self.agent_config.max_steps:
            result = self._step()
            if result.finished:
                return result.message or "Task completed"

        return "Max steps reached"

    def step(self, task: str | None = None) -> StepResult:
        """Execute a single step (for manual control)."""
        is_first = len(self._context) == 0
        if is_first and not task:
            raise ValueError("Task is required for the first step")
        return self._step(task, is_first)

    def reset(self) -> None:
        """Reset agent state."""
        self._context = []
        self._step_count = 0

    def _execute_step(
        self, user_prompt: str | None = None, is_first: bool = False
    ) -> StepResult:
        """Execute a single step of the agent loop."""
        self._step_count += 1

        # Capture current screen state
        screenshot = get_screenshot(self.agent_config.device_id)
        current_app = get_current_app(self.agent_config.device_id)

        # 2. Build context
        self._build_context(user_prompt, current_app, screenshot, is_first)

        # 3. Get model response
        response = self._get_model_response()
        if response is None:
            return self._handle_error("Model request failed", screenshot.height)

        # 4. Parse action
        action = self._parse_action(response.action)
        if action is None:
            return self._handle_error(f"Parse failed: {response.action}", screenshot.height)

        # 5. Check if stuck in loop
        action = self._check_and_recover(action, screenshot.height)

        # Get model response
        try:
            response = self.model_client.request(self._context)
        except Exception as e:
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
        except ValueError:
            if self.agent_config.verbose:
                traceback.print_exc()
            action = finish(message=response.action)

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
            result = self.action_handler.execute(
                action, screenshot.width, screenshot.height
            )
        except Exception as e:
            if self.agent_config.verbose:
                traceback.print_exc()
            result = self.action_handler.execute(
                finish(message=str(e)), screenshot.width, screenshot.height
            )

        # 9. Add assistant response to context
        self._context.append(
            MessageBuilder.create_assistant_message(
                f"<think>{response.thinking}</think><answer>{response.action}</answer>"
            )
        )

        # 10. Check completion
        finished = action.get("_metadata") == "finish" or result.should_finish
        if finished:
            self._log(f"\n✅ Task completed: {result.message or action.get('message', 'Done')}")

        # Reset error tracking on success
        if result.success:
            self._state.reset_errors()

        return StepResult(
            success=result.success,
            finished=finished,
            action=action,
            thinking=response.thinking,
            message=result.message or action.get("message"),
        )

    def _build_context(self, user_prompt: str | None, current_app: str, screenshot, is_first: bool) -> None:
        """Build conversation context."""
        screen_info = MessageBuilder.build_screen_info(current_app)

        if is_first:
            self._context.append(
                MessageBuilder.create_system_message(self.agent_config.system_prompt)
            )
            text_content = f"{user_prompt}\n\n{screen_info}"
        else:
            text_content = f"** Screen Info **\n\n{screen_info}"

        self._context.append(
            MessageBuilder.create_user_message(
                text=text_content, image_base64=screenshot.base64_data
            )
        )

    def _get_model_response(self):
        """Get response from model."""
        try:
            return self.model_client.request(self._context)
        except Exception as e:
            self._log(f"Model error: {e}")
            return None

    def _parse_action(self, action_str: str) -> dict[str, Any] | None:
        """Parse action from response."""
        try:
            return parse_action(action_str)
        except ValueError as e:
            self._log(f"Parse error: {e}")
            return None

    def _check_and_recover(self, action: dict[str, Any], screen_height: int) -> dict[str, Any]:
        """Check if stuck and apply recovery if needed."""
        # Create action signature
        sig = f"{action.get('action')}:{action.get('element', action.get('startPoint', ''))}"
        self._state.record(sig)

        # Check if stuck
        if self._state.is_stuck(self.agent_config.max_repeat):
            self._log(f"⚠️ Loop detected: {sig} repeated {self.agent_config.max_repeat} times")
            return self._get_recovery_action(screen_height)

        return action

    def _handle_error(self, error: str, screen_height: int) -> StepResult:
        """Handle errors with recovery."""
        self._log(f"Error: {error}")

        if self._state.record_error(error):
            self._log("⚠️ Same error repeated 3 times, attempting recovery")
            action = self._get_recovery_action(screen_height)
            result = self.action_handler.execute(action, 1080, screen_height)
            self._state.reset_errors()
            return StepResult(success=False, finished=False, action=action, thinking="", message=error)

        # Simple wait on first errors
        action = do(action="Wait", duration="2 seconds")
        self.action_handler.execute(action, 1080, screen_height)
        return StepResult(success=False, finished=False, action=action, thinking="", message=error)

    def _get_recovery_action(self, screen_height: int) -> dict[str, Any]:
        """Get a recovery action to break out of stuck state."""
        idx = self._state.recovery_attempts % len(self.RECOVERY_ACTIONS)
        name, action_fn = self.RECOVERY_ACTIONS[idx]
        self._state.recovery_attempts += 1
        self._state.history.clear()  # Clear history after recovery

        self._log(f"Recovery action: {name}")
        return action_fn(screen_height)

    def _display_response(self, thinking: str, action: dict[str, Any]) -> None:
        """Display model response."""
        if not self.agent_config.verbose:
            return

        msgs = get_messages(self.agent_config.lang)
        print(f"\n💭 {msgs['thinking']}:")
        print("-" * 40)
        print(thinking if thinking else "(no thinking)")
        print("-" * 40)
        print(f"🎯 {msgs['action']}:")
        print(json.dumps(action, ensure_ascii=False, indent=2))

    def _log(self, msg: str) -> None:
        """Log message if verbose."""
        if self.agent_config.verbose:
            print(msg)

    @property
    def context(self) -> list[dict[str, Any]]:
        """Get current conversation context."""
        return self._context.copy()

    @property
    def step_count(self) -> int:
        """Get current step count."""
        return self._step_count
