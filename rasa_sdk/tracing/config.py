from __future__ import annotations

import abc
import logging
import os
from typing import Any, Dict, Optional, Text

import grpc
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from rasa_sdk.tracing.endpoints import EndpointConfig, read_endpoint_config
from rasa_sdk.tracing.instrumentation import instrumentation
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.forms import ValidationAction, FormValidationAction

TRACING_SERVICE_NAME = os.environ.get("RASA_SDK_TRACING_SERVICE_NAME", "rasa_sdk")

ENDPOINTS_TRACING_KEY = "tracing"

logger = logging.getLogger(__name__)


def configure_tracing(tracer_provider: Optional[TracerProvider]) -> None:
    """Configure tracing functionality.

    When a tracing backend is defined, this function will
    instrument all methods that shall be traced.
    If no tracing backend is defined, no tracing is configured.

    :param tracer_provider: The `TracingProvider` to be used for tracing
    """
    if tracer_provider is None:
        return None

    instrumentation.instrument(
        tracer_provider=tracer_provider,
        action_executor_class=ActionExecutor,
        validation_action_class=ValidationAction,
        form_validation_action_class=FormValidationAction,
    )


def get_tracer_provider(endpoints_file: Text) -> Optional[TracerProvider]:
    """Configure tracing backend.

    When a known tracing backend is defined in the endpoints file, this
    function will configure the tracing infrastructure. When no or an unknown
    tracing backend is defined, this function does nothing.

    :param endpoints_file: The configuration file containing information about the
        tracing backend.
    :return: The `TracingProvider` to be used for all subsequent tracing.
    """
    cfg = read_endpoint_config(endpoints_file, ENDPOINTS_TRACING_KEY)

    if not cfg:
        logger.info(
            f"No endpoint for tracing type available in {endpoints_file},"
            f"tracing will not be configured."
        )
        return None
    if cfg.type == "jaeger":
        tracer_provider = JaegerTracerConfigurer.configure_from_endpoint_config(cfg)
    elif cfg.type == "otlp":
        tracer_provider = OTLPCollectorConfigurer.configure_from_endpoint_config(cfg)
    else:
        logger.warning(
            f"Unknown tracing type {cfg.type} read from {endpoints_file}, ignoring."
        )
        return None

    return tracer_provider


class TracerConfigurer(abc.ABC):
    """Abstract superclass for tracing configuration.

    `TracerConfigurer` is the abstract superclass from which all configurers
    for different supported backends should inherit.
    """

    @classmethod
    @abc.abstractmethod
    def configure_from_endpoint_config(cls, cfg: EndpointConfig) -> TracerProvider:
        """Configure tracing.

        This abstract method should be implemented by all concrete `TracerConfigurer`s.
        It shall read the configuration from the supplied argument, configure all
        necessary infrastructure for tracing, and return the `TracerProvider` to be
        used for tracing purposes.

        :param cfg: The configuration to be read for configuring tracing.
        :return: The configured `TracerProvider`.
        """


class JaegerTracerConfigurer(TracerConfigurer):
    """The `TracerConfigurer` for a Jaeger backend."""

    @classmethod
    def configure_from_endpoint_config(cls, cfg: EndpointConfig) -> TracerProvider:
        """Configure tracing for Jaeger.

        This will read the Jaeger-specific configuration from the `EndpointConfig` and
        create a corresponding `TracerProvider` that exports to the given Jaeger
        backend.

        :param cfg: The configuration to be read for configuring tracing.
        :return: The configured `TracerProvider`.
        """
        provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: TRACING_SERVICE_NAME})
        )

        jaeger_exporter = JaegerExporter(
            **cls._extract_config(cfg), udp_split_oversized_batches=True
        )
        logger.info(
            f"Registered {cfg.type} endpoint for tracing. Traces will be exported to"
            f" {jaeger_exporter.agent_host_name}:{jaeger_exporter.agent_port}"
        )
        provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

        return provider

    @classmethod
    def _extract_config(cls, cfg: EndpointConfig) -> Dict[str, Any]:
        return {
            "agent_host_name": (cfg.kwargs.get("host", "localhost")),
            "agent_port": (cfg.kwargs.get("port", 6831)),
            "username": cfg.kwargs.get("username"),
            "password": cfg.kwargs.get("password"),
        }


class OTLPCollectorConfigurer(TracerConfigurer):
    """The `TracerConfigurer` for an OTLP collector backend."""

    @classmethod
    def configure_from_endpoint_config(cls, cfg: EndpointConfig) -> TracerProvider:
        """Configure tracing for Jaeger.

        This will read the OTLP collector-specific configuration from the
        `EndpointConfig` and create a corresponding `TracerProvider` that exports to
        the given OTLP collector.
        Currently, this only supports insecure connections via gRPC.

        :param cfg: The configuration to be read for configuring tracing.
        :return: The configured `TracerProvider`.
        """
        provider = TracerProvider(
            resource=Resource.create({SERVICE_NAME: TRACING_SERVICE_NAME})
        )

        insecure = cfg.kwargs.get("insecure")

        credentials = cls._get_credentials(cfg, insecure)  # type: ignore

        otlp_exporter = OTLPSpanExporter(
            endpoint=cfg.kwargs["endpoint"],
            insecure=insecure,
            credentials=credentials,
        )
        logger.info(
            f"Registered {cfg.type} endpoint for tracing."
            f"Traces will be exported to {cfg.kwargs['endpoint']}"
        )
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        return provider

    @classmethod
    def _get_credentials(
        cls, cfg: EndpointConfig, insecure: bool
    ) -> Optional[grpc.ChannelCredentials]:
        credentials = None
        if not insecure and "root_certificates" in cfg.kwargs:
            with open(cfg.kwargs.get("root_certificates"), "rb") as f:  # type: ignore
                root_cert = f.read()
            credentials = grpc.ssl_channel_credentials(root_certificates=root_cert)
        return credentials
