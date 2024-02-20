import functools
import inspect
import json
import logging
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
    Text,
    Type,
    TypeVar,
    Union,
)

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.trace import Tracer
from rasa_sdk import Tracker
from rasa_sdk.executor import ActionExecutor, CollectingDispatcher
from rasa_sdk.events import EventType
from rasa_sdk.forms import ValidationAction, FormValidationAction
from rasa_sdk.tracing.instrumentation import attribute_extractors
from rasa_sdk.tracing.tracer_register import ActionExecutorTracerRegister
from rasa_sdk.types import DomainDict


# The `TypeVar` representing the return type for a function to be wrapped.
S = TypeVar("S")
# The `TypeVar` representing the type of the argument passed to the function to be
# wrapped.
T = TypeVar("T")

logger = logging.getLogger(__name__)
INSTRUMENTED_BOOLEAN_ATTRIBUTE_NAME = "class_has_been_instrumented"


def _check_extractor_argument_list(
    fn: Callable[[T, Any, Any], S],
    attr_extractor: Optional[Callable[[T, Any, Any], Dict[str, Any]]],
) -> bool:
    if attr_extractor is None:
        return False

    fn_args = inspect.signature(fn)
    attr_args = inspect.signature(attr_extractor)

    are_arglists_congruent = fn_args.parameters.keys() == attr_args.parameters.keys()

    if not are_arglists_congruent:
        logger.warning(
            f"Argument lists for {fn.__name__} and {attr_extractor.__name__}"
            f" do not match up. {fn.__name__} will be traced without attributes."
        )

    return are_arglists_congruent


def traceable_async(
    fn: Callable[[T, Any, Any], Awaitable[S]],
    tracer: Tracer,
    attr_extractor: Optional[Callable[[T, Any, Any], Dict[str, Any]]],
) -> Callable[[T, Any, Any], Awaitable[S]]:
    """Wrap an `async` function by tracing functionality.

    :param fn: The function to be wrapped.
    :param tracer: The `Tracer` that shall be used for tracing this function.
    :param attr_extractor: A function that is applied to the function's instance and
        the function's arguments.
    :return: The wrapped function.
    """
    should_extract_args = _check_extractor_argument_list(fn, attr_extractor)

    @functools.wraps(fn)
    async def async_wrapper(self: T, *args: Any, **kwargs: Any) -> S:
        attrs = (
            attr_extractor(self, *args, **kwargs)
            if attr_extractor and should_extract_args
            else {}
        )
        if issubclass(self.__class__, FormValidationAction):
            span_name = f"FormValidationAction.{self.__class__.__name__}.{fn.__name__}"
        elif issubclass(self.__class__, ValidationAction):
            span_name = f"ValidationAction.{self.__class__.__name__}.{fn.__name__}"
        else:
            span_name = f"{self.__class__.__name__}.{fn.__name__}"
        with tracer.start_as_current_span(span_name, attributes=attrs):
            return await fn(self, *args, **kwargs)

    return async_wrapper


def traceable(
    fn: Callable[[T, Any, Any], S],
    tracer: Tracer,
    attr_extractor: Optional[Callable[[T, Any, Any], Dict[str, Any]]],
) -> Callable[[T, Any, Any], S]:
    """Wrap a non-`async` function by tracing functionality.

    :param fn: The function to be wrapped.
    :param tracer: The `Tracer` that shall be used for tracing this function.
    :param attr_extractor: A function that is applied to the function's instance and
        the function's arguments.
    :return: The wrapped function.
    """
    should_extract_args = _check_extractor_argument_list(fn, attr_extractor)

    @functools.wraps(fn)
    def wrapper(self: T, *args: Any, **kwargs: Any) -> S:
        # the conditional statement is needed because
        # _create_api_response is a static method
        if isinstance(self, ActionExecutor) and fn.__name__ == "_create_api_response":
            attrs = (
                attr_extractor(*args, **kwargs)
                if attr_extractor and should_extract_args
                else {}
            )
        else:
            attrs = (
                attr_extractor(self, *args, **kwargs)
                if attr_extractor and should_extract_args
                else {}
            )
        with tracer.start_as_current_span(
            f"{self.__class__.__name__}.{fn.__name__}", attributes=attrs
        ):
            if (
                isinstance(self, ActionExecutor)
                and fn.__name__ == "_create_api_response"
            ):
                return fn(*args, **kwargs)
            return fn(self, *args, **kwargs)

    return wrapper


ActionExecutorType = TypeVar("ActionExecutorType", bound=ActionExecutor)
ValidationActionType = TypeVar("ValidationActionType", bound=ValidationAction)
FormValidationActionType = TypeVar(
    "FormValidationActionType", bound=FormValidationAction
)


def instrument(
    tracer_provider: TracerProvider,
    action_executor_class: Optional[Type[ActionExecutorType]] = None,
    validation_action_class: Optional[Type[ValidationActionType]] = None,
    form_validation_action_class: Optional[Type[FormValidationActionType]] = None,
) -> None:
    """Substitute methods to be traced by their traced counterparts.

    :param tracer_provider: The `TracerProvider` to be used for configuring tracing
        on the substituted methods.
    :param action_executor_class: The `ActionExecutor` to be instrumented. If `None`
        is given, no `ActionExecutor` will be instrumented.
    :param validation_action_class: The `ValidationAction` to be instrumented. If `None`
        is given, no `ValidationAction` will be instrumented.
    :param form_validation_action_class: The `FormValidationAction` to be instrumented.
        If `None` is given, no `FormValidationAction` will be instrumented.
    """
    if action_executor_class is not None and not class_is_instrumented(
        action_executor_class
    ):
        tracer = tracer_provider.get_tracer(action_executor_class.__module__)
        _instrument_method(
            tracer,
            action_executor_class,
            "run",
            attribute_extractors.extract_attrs_for_action_executor,
        )
        _instrument_method(
            tracer,
            action_executor_class,
            "_create_api_response",
            attribute_extractors.extract_attrs_for_action_executor_create_api_response,
        )
        mark_class_as_instrumented(action_executor_class)
        ActionExecutorTracerRegister().register_tracer(tracer)

    if validation_action_class is not None and not class_is_instrumented(
        validation_action_class
    ):
        _instrument_method(
            tracer_provider.get_tracer(validation_action_class.__module__),
            validation_action_class,
            "run",
            attribute_extractors.extract_attrs_for_validation_action,
        )
        _instrument_validation_action_extract_validation_events(
            tracer_provider.get_tracer(validation_action_class.__module__),
            validation_action_class,
        )
        mark_class_as_instrumented(validation_action_class)

    if form_validation_action_class is not None and not class_is_instrumented(
        form_validation_action_class
    ):
        _instrument_validation_action_extract_validation_events(
            tracer_provider.get_tracer(form_validation_action_class.__module__),
            form_validation_action_class,
        )
        mark_class_as_instrumented(form_validation_action_class)


def _instrument_method(
    tracer: Tracer,
    instrumented_class: Type,
    method_name: Text,
    attr_extractor: Optional[Callable],
) -> None:
    method_to_trace = getattr(instrumented_class, method_name)
    if inspect.iscoroutinefunction(method_to_trace):
        traced_method = traceable_async(method_to_trace, tracer, attr_extractor)
    else:
        traced_method = traceable(method_to_trace, tracer, attr_extractor)
    setattr(instrumented_class, method_name, traced_method)

    logger.debug(f"Instrumented '{instrumented_class.__name__}.{method_name}'.")


def _mangled_instrumented_boolean_attribute_name(instrumented_class: Type) -> Text:
    # see https://peps.python.org/pep-0008/#method-names-and-instance-variables
    # and https://stackoverflow.com/a/50401073
    return f"_{instrumented_class.__name__}__{INSTRUMENTED_BOOLEAN_ATTRIBUTE_NAME}"


def class_is_instrumented(instrumented_class: Type) -> bool:
    """Check if a class has already been instrumented."""
    return getattr(
        instrumented_class,
        _mangled_instrumented_boolean_attribute_name(instrumented_class),
        False,
    )


def mark_class_as_instrumented(instrumented_class: Type) -> None:
    """Mark a class as instrumented if it isn't already marked."""
    if not class_is_instrumented(instrumented_class):
        setattr(
            instrumented_class,
            _mangled_instrumented_boolean_attribute_name(instrumented_class),
            True,
        )


def _instrument_validation_action_extract_validation_events(
    tracer: Tracer,
    validation_action_class: Union[Type[ValidationAction], Type[FormValidationAction]],
) -> None:
    def tracing_validation_action_extract_validation_events_wrapper(
        fn: Callable,
    ) -> Callable:
        @functools.wraps(fn)
        async def wrapper(
            self,
            dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: DomainDict,
        ) -> List[EventType]:
            if issubclass(self.__class__, FormValidationAction):
                span_name = (
                    f"FormValidationAction.{self.__class__.__name__}.{fn.__name__}"
                )
            else:
                span_name = f"ValidationAction.{self.__class__.__name__}.{fn.__name__}"

            with tracer.start_as_current_span(span_name) as span:
                validation_events = await fn(self, dispatcher, tracker, domain)
                event_names = []
                slot_names = []

                if validation_events:
                    for event in validation_events:
                        event_names.append(event.get("event"))
                        if event.get("event") == "slot":
                            slot_names.append(event.get("name"))

                span.set_attributes(
                    {
                        "validation_events": json.dumps(
                            list(dict.fromkeys(event_names))
                        ),
                        "slots": json.dumps(list(dict.fromkeys(slot_names))),
                    }
                )
                return validation_events

        return wrapper

    validation_action_class._extract_validation_events = (  # type: ignore
        tracing_validation_action_extract_validation_events_wrapper(
            validation_action_class._extract_validation_events
        )
    )

    logger.debug(
        f"Instrumented '{validation_action_class.__name__}._extract_validation_events'."
    )
