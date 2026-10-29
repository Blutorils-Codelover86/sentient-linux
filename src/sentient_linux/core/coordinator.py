"""
Central Command Coordinator for Sentient Linux.
Orchestrates perception, reasoning, safety policy, and computer use.
"""

from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from sentient_linux.core.state_machine import StateMachine, SentientState
from sentient_linux.core.events import (
    EventBus,
    StateChangedEvent,
    ContextCapturedEvent,
    EmergencyStopTriggeredEvent,
    ErrorEvent,
)
from sentient_linux.perception.context import ContextManager, DesktopContext
from sentient_linux.perception.hyprland import HyprlandInspector
from sentient_linux.perception.screenshots import ScreenshotEngine
from sentient_linux.inference.router import InferenceRouter
from sentient_linux.computer_use.action_schema import ProposedAction
from sentient_linux.computer_use.supervisor import ActionSupervisor
from sentient_linux.security.emergency_stop import EmergencyStop
from sentient_linux.security.policy import SecurityPolicy
from sentient_linux.security.privacy import ConsentManager

logger = logging.getLogger("sentient.core.coordinator")


class CommandCoordinator:
    """
    Coordinates desktop AI assistance lifecycle.
    Enforces that all actions flow through deterministic safety boundaries.
    """

    def __init__(
        self,
        inspector: Optional[HyprlandInspector] = None,
        screenshots: Optional[ScreenshotEngine] = None,
        inference: Optional[InferenceRouter] = None,
        supervisor: Optional[ActionSupervisor] = None,
        policy: Optional[SecurityPolicy] = None,
        consent_manager: Optional[ConsentManager] = None,
        event_bus: Optional[EventBus] = None,
        model: Optional[str] = None,
        provider: Optional[str] = None,
    ) -> None:
        self.emergency_stop = EmergencyStop()
        self.state_machine = StateMachine()
        self.event_bus = event_bus or EventBus()

        self.policy = policy or SecurityPolicy()
        self.consent_manager = consent_manager or ConsentManager()
        self.inspector = inspector or HyprlandInspector()
        self.screenshots = screenshots or ScreenshotEngine()
        self.context_manager = ContextManager(self.inspector, self.screenshots)
        self.inference = inference or InferenceRouter(
            provider=provider,
            model=model,
            consent_manager=self.consent_manager,
        )
        self.supervisor = supervisor or ActionSupervisor(policy=self.policy)

    @property
    def active_model(self) -> str:
        return self.inference.active_model

    def set_model(self, model_name: str) -> None:
        self.inference.set_model(model_name)

    def list_models(self) -> list[str]:
        return self.inference.list_available_models()

    def _set_state(self, new_state: SentientState) -> None:
        old_state = self.state_machine.current_state
        self.state_machine.transition_to(new_state)
        self.event_bus.publish(StateChangedEvent(old_state=old_state, new_state=new_state))

    def ask(
        self,
        prompt: str,
        include_context: bool = True,
        include_screenshot: bool = False,
    ) -> str:
        """
        Process a user prompt with desktop perception and inference.
        Guarantees that screenshots are taken on explicit request only and
        temporary files are deterministically cleaned up.
        """
        self.emergency_stop.check()

        context: Optional[DesktopContext] = None
        try:
            self._set_state(SentientState.PERCEIVING)
            if include_context:
                context = self.context_manager.snapshot(include_screenshot=include_screenshot)
                app_title = context.focused_window.title if context.focused_window else "None"
                self.event_bus.publish(
                    ContextCapturedEvent(
                        focused_app=app_title,
                        open_window_count=len(context.windows),
                        has_screenshot=bool(context.screenshot),
                    )
                )

            self._set_state(SentientState.REASONING)

            assembled_prompt = prompt
            image_path = None
            if context:
                assembled_prompt = f"{context.to_prompt_context()}\n\n[USER INSTRUCTION]\n{prompt}"
                if context.screenshot:
                    image_path = context.screenshot.path

            response = self.inference.ask(
                prompt=assembled_prompt,
                image_path=image_path,
            )

            self._set_state(SentientState.FINISHING)
            self._set_state(SentientState.IDLE)
            return response

        except Exception as err:
            self._set_state(SentientState.ERROR)
            self.event_bus.publish(ErrorEvent(error_type=type(err).__name__, message=str(err)))
            raise

        finally:
            # Deterministic cleanup of temporary screenshot
            if context and context.screenshot:
                context.screenshot.cleanup()

    def execute_action(self, action: ProposedAction) -> Dict[str, Any]:
        """Supervised action execution."""
        self.emergency_stop.check()
        self._set_state(SentientState.EXECUTING)
        try:
            result = self.supervisor.execute_action(action)
            self._set_state(SentientState.IDLE)
            return result
        except Exception as err:
            self._set_state(SentientState.ERROR)
            self.event_bus.publish(ErrorEvent(error_type=type(err).__name__, message=str(err)))
            raise

    def stop(self, reason: str = "User initiated STOP") -> int:
        """Trigger emergency stop immediately."""
        count = self.emergency_stop.trigger(reason)
        self._set_state(SentientState.STOPPED)
        self.event_bus.publish(EmergencyStopTriggeredEvent(reason=reason, processes_terminated=count))
        return count

    def reset(self) -> None:
        """Reset emergency stop and return to IDLE."""
        self.emergency_stop.reset()
        self.state_machine.reset()
