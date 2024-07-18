from typing import Optional
from rasa_sdk.utils import Singleton
from opentelemetry.trace import Tracer


class ActionExecutorTracerRegister(metaclass=Singleton):
    """Represents a provider for ActionExecutor tracer."""

    tracer: Optional[Tracer] = None

    def register_tracer(self, tracer: Tracer) -> None:
        """Register an ActionExecutor tracer.

        Args:
            tracer: The tracer to register.
        """
        self.tracer = tracer

    def get_tracer(self) -> Optional[Tracer]:
        """Get the ActionExecutor tracer.

        Returns:
            The tracer.
        """
        return self.tracer
