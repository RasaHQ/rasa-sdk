import logging

import os
from typing import Any, Dict, Optional, Text
import rasa_sdk.utils


logger = logging.getLogger(__name__)
DEFAULT_ENCODING = "utf-8"


def read_endpoint_config(
    filename: Text, endpoint_type: Text
) -> Optional["EndpointConfig"]:
    """Read an endpoint configuration file from disk and extract one config.

    Args:
        filename: the endpoint config file to read
        endpoint_type: the type of the endpoint

    Returns:
        The endpoint configuration of the passed type if it exists, `None` otherwise.
    """
    if not filename:
        return None

    try:
        content = rasa_sdk.utils.read_file(filename)
        content = rasa_sdk.utils.read_yaml(content)

        if content.get(endpoint_type) is None:
            return None

        return EndpointConfig.from_dict(content[endpoint_type])
    except FileNotFoundError:
        logger.error(
            "Failed to read endpoint configuration " "from {}. No such file.".format(
                os.path.abspath(filename)
            )
        )
        return None


class EndpointConfig:
    """Configuration for an external HTTP endpoint."""

    def __init__(
        self,
        url: Optional[Text] = None,
        params: Optional[Dict[Text, Any]] = None,
        headers: Optional[Dict[Text, Any]] = None,
        basic_auth: Optional[Dict[Text, Text]] = None,
        token: Optional[Text] = None,
        token_name: Text = "token",
        cafile: Optional[Text] = None,
        **kwargs: Any,
    ) -> None:
        """Creates an `EndpointConfig` instance."""
        self.url = url
        self.params = params or {}
        self.headers = headers or {}
        self.basic_auth = basic_auth or {}
        self.token = token
        self.token_name = token_name
        self.type = kwargs.pop("store_type", kwargs.pop("type", None))
        self.cafile = cafile
        self.kwargs = kwargs

    @classmethod
    def from_dict(cls, data: Dict[Text, Any]) -> "EndpointConfig":
        return EndpointConfig(**data)
