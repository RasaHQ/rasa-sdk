import argparse
import logging
import os
import types
import zlib
import json
from typing import List, Text, Union, Optional, Any, Dict
import ssl
from ssl import SSLContext

from sanic import Sanic, response
from sanic.response import HTTPResponse
from sanic.request import Request
from sanic_cors import CORS
import aiohttp 
from aiohttp.client_exceptions import ContentTypeError

from rasa_sdk import utils
from rasa_sdk.cli.arguments import add_endpoint_arguments
from rasa_sdk.constants import DEFAULT_SERVER_PORT
from rasa_sdk.executor import ActionExecutor
from rasa_sdk.interfaces import ActionExecutionRejection, ActionNotFoundException
from rasa_sdk.exceptions import FileNotFoundException

from urllib import parse

logger = logging.getLogger(__name__)

######### BLOCK INSERTION

DOMAIN_ENDPOINT: str = os.environ("DOMAIN_ENDPOINT", "") # DOMAIN_ENDPOINT=http://rasa.server/domain:5055?token=TOKEN
DEFAULT_REQUEST_TIMEOUT: int = 7 # give 7 seconds respone time for a domain API answer

# copied from rasa.utils.endpoints
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

    def session(self) -> aiohttp.ClientSession:
        """Creates and returns a configured aiohttp client session."""
        # create authentication parameters
        if self.basic_auth:
            auth = aiohttp.BasicAuth(
                self.basic_auth["username"], self.basic_auth["password"]
            )
        else:
            auth = None

        return aiohttp.ClientSession(
            headers=self.headers,
            auth=auth,
            timeout=aiohttp.ClientTimeout(total=DEFAULT_REQUEST_TIMEOUT),
        )

    def combine_parameters(
        self, kwargs: Optional[Dict[Text, Any]] = None
    ) -> Dict[Text, Any]:
        # construct GET parameters
        params = self.params.copy()

        # set the authentication token if present
        if self.token:
            params[self.token_name] = self.token

        if kwargs and "params" in kwargs:
            params.update(kwargs["params"])
            del kwargs["params"]
        return params

    async def request(
        self,
        method: Text = "post",
        subpath: Optional[Text] = None,
        content_type: Optional[Text] = "application/json",
        **kwargs: Any,
    ) -> Optional[Any]:
        """Send a HTTP request to the endpoint. Return json response, if available.

        All additional arguments will get passed through
        to aiohttp's `session.request`."""

        # create the appropriate headers
        headers = {}
        if content_type:
            headers["Content-Type"] = content_type

        if "headers" in kwargs:
            headers.update(kwargs["headers"])
            del kwargs["headers"]

        url = concat_url(self.url, subpath)

        sslcontext = None
        if self.cafile:
            try:
                sslcontext = ssl.create_default_context(cafile=self.cafile)
            except FileNotFoundError as e:
                raise FileNotFoundException(
                    f"Failed to find certificate file, "
                    f"'{os.path.abspath(self.cafile)}' does not exist."
                ) from e

        async with self.session() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                params=self.combine_parameters(kwargs),
                ssl=sslcontext,
                **kwargs,
            ) as response:
                if response.status >= 400:
                    raise ClientResponseError(
                        response.status, response.reason, await response.content.read()
                    )
                try:
                    return await response.json()
                except ContentTypeError:
                    return None

    @classmethod
    def from_dict(cls, data: Dict[Text, Any]) -> "EndpointConfig":
        return EndpointConfig(**data)

    def copy(self) -> "EndpointConfig":
        return EndpointConfig(
            self.url,
            self.params,
            self.headers,
            self.basic_auth,
            self.token,
            self.token_name,
            **self.kwargs,
        )

    def __eq__(self, other: Any) -> bool:
        if isinstance(self, type(other)):
            return (
                other.url == self.url
                and other.params == self.params
                and other.headers == self.headers
                and other.basic_auth == self.basic_auth
                and other.token == self.token
                and other.token_name == self.token_name
            )
        else:
            return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

# copied from rasa.utils.endpoints
class ClientResponseError(aiohttp.ClientError):
    def __init__(self, status: int, message: Text, text: Text) -> None:
        self.status = status
        self.message = message
        self.text = text
        super().__init__(f"{status}, {message}, body='{text}'")

# copied from rasa.utils.endpoints
def concat_url(base: Text, subpath: Optional[Text]) -> Text:
    """Append a subpath to a base url.

    Strips leading slashes from the subpath if necessary. This behaves
    differently than `urlparse.urljoin` and will not treat the subpath
    as a base url if it starts with `/` but will always append it to the
    `base`.

    Args:
        base: Base URL.
        subpath: Optional path to append to the base URL.

    Returns:
        Concatenated URL with base and subpath.
    """
    if not subpath:
        if base.endswith("/"):
            logger.debug(
                f"The URL '{base}' has a trailing slash. Please make sure the "
                f"target server supports trailing slashes for this endpoint."
            )
        return base

    url = base
    if not base.endswith("/"):
        url += "/"
    if subpath.startswith("/"):
        subpath = subpath[1:]
    return url + subpath

local_domain = dict()
domain_endpoint = None

if DOMAIN_ENDPOINT: 
    # TODO that could be a file URL to be loaded, like in rasa.utils.endpoints.read_endpoint_config()
    if isinstance(DOMAIN_ENDPOINT, str) and DOMAIN_ENDPOINT.startswith("http"):
        parts = parse.urlparse(DOMAIN_ENDPOINT)
        query = parts.query
        query_params = {k:(v[0] if len(v)==1 else v) for k,v in parse.parse_qs(query)}
        parts.query = ''
        parts.fragment = ''
        url = parse.urlunparse(parts)
        token = {}
        if t:=query_params.get("token"):
            # special case for token
            token["token_name"]="token"
            token["token"]=t
            del query_params["token"]
        logger.debug(f"{url=} {query_params=} {token=}")
        domain_endpoint = EndpointConfig(url=url,  params=query_params, **token)

async def get_domain()->dict:
    if local_domain:
        # use cached
        return local_domain
    if domain_endpoint:
        # create a request towards the endpoint which can deliver a domain JSON
        try:
            logger.debug(f"Accessing domain endpoint at {DOMAIN_ENDPOINT}")
            response: Any = await domain_endpoint.request(
                method="get", timeout=DEFAULT_REQUEST_TIMEOUT
            )            
            if "intents" in response:
                # very simple check if it is a domain objects
                local_domain = response # put in cache
                return local_domain
        except ClientResponseError as ex:
                logger.error(f"Retrieval of domain was unsuccessful, {ex.message=} {ex.status=} {ex.text=}", exc_info=ex)
                return 
        except Exception as e:
                logger.error(f"Retrieval of domain was unsuccessful, {e.args=}", exc_info=ex)
                return             




########## END BLOCK INSERTION
def configure_cors(
    app: Sanic, cors_origins: Union[Text, List[Text], None] = ""
) -> None:
    """Configure CORS origins for the given app."""

    CORS(
        app, resources={r"/*": {"origins": cors_origins or ""}}, automatic_options=True
    )


def create_ssl_context(
    ssl_certificate: Optional[Text],
    ssl_keyfile: Optional[Text],
    ssl_password: Optional[Text] = None,
) -> Optional[SSLContext]:
    """Create a SSL context if a certificate is passed."""

    if ssl_certificate:
        import ssl

        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(
            ssl_certificate, keyfile=ssl_keyfile, password=ssl_password
        )
        return ssl_context
    else:
        return None


def create_argument_parser():
    """Parse all the command line arguments for the run script."""

    parser = argparse.ArgumentParser(description="starts the action endpoint")
    add_endpoint_arguments(parser)
    utils.add_logging_level_option_arguments(parser)
    utils.add_logging_file_arguments(parser)
    return parser


def create_app(
    action_package_name: Union[Text, types.ModuleType],
    cors_origins: Union[Text, List[Text], None] = "*",
    auto_reload: bool = False,
) -> Sanic:
    """Create a Sanic application and return it.

    Args:
        action_package_name: Name of the package or module to load actions
            from.
        cors_origins: CORS origins to allow.
        auto_reload: When `True`, auto-reloading of actions is enabled.

    Returns:
        A new Sanic application ready to be run.
    """
    app = Sanic("rasa_sdk", configure_logging=False)

    configure_cors(app, cors_origins)

    executor = ActionExecutor()
    executor.register_package(action_package_name)

    @app.get("/health")
    async def health(_) -> HTTPResponse:
        """Ping endpoint to check if the server is running and well."""
        body = {"status": "ok"}
        return response.json(body, status=200)

    @app.post("/webhook")
    async def webhook(request: Request) -> HTTPResponse:
        """Webhook to retrieve action calls."""
        if request.headers.get("Content-Encoding") == "deflate":
            # Decompress the request data using zlib
            decompressed_data = zlib.decompress(request.body)
            # Load the JSON data from the decompressed request data
            action_call = json.loads(decompressed_data)
        else:
            action_call = request.json
            

        if action_call is None:
            body = {"error": "Invalid body request"}
            return response.json(body, status=400)

        utils.check_version_compatibility(action_call.get("version"))

        if auto_reload:
            executor.reload()

        if not action_call.get("domain"):
            # no domain send by Rasa OSS, so use chached one or try to acquire one from endpoint
            domain = await get_domain()
            if domain:
                action_call["domain"] = domain

        try:
            result = await executor.run(action_call)
        except ActionExecutionRejection as e:
            logger.debug(e)
            body = {"error": e.message, "action_name": e.action_name}
            return response.json(body, status=400)
        except ActionNotFoundException as e:
            logger.error(e)
            body = {"error": e.message, "action_name": e.action_name}
            return response.json(body, status=404)

        return response.json(result, status=200)

    @app.get("/actions")
    async def actions(_) -> HTTPResponse:
        """List all registered actions."""
        if auto_reload:
            executor.reload()

        body = [{"name": k} for k in executor.actions.keys()]
        return response.json(body, status=200)

    @app.exception(Exception)
    async def exception_handler(request, exception: Exception):
        logger.error(
            msg=f"Exception occurred during execution of request {request}",
            exc_info=exception,
        )
        body = {"error": str(exception), "request_body": request.json}
        return response.json(body, status=500)

    return app


def run(
    action_package_name: Union[Text, types.ModuleType],
    port: int = DEFAULT_SERVER_PORT,
    cors_origins: Union[Text, List[Text], None] = "*",
    ssl_certificate: Optional[Text] = None,
    ssl_keyfile: Optional[Text] = None,
    ssl_password: Optional[Text] = None,
    auto_reload: bool = False,
) -> None:
    """Starts the action endpoint server with given config values."""
    logger.info("Starting action endpoint server...")
    app = create_app(
        action_package_name, cors_origins=cors_origins, auto_reload=auto_reload
    )
    ssl_context = create_ssl_context(ssl_certificate, ssl_keyfile, ssl_password)
    protocol = "https" if ssl_context else "http"
    host = os.environ.get("SANIC_HOST", "0.0.0.0")

    logger.info(f"Action endpoint is up and running on {protocol}://{host}:{port}")
    app.run(host, port, ssl=ssl_context, workers=utils.number_of_sanic_workers())


if __name__ == "__main__":
    import rasa_sdk.__main__

    rasa_sdk.__main__.main()
