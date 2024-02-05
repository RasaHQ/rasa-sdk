import rasa_sdk.endpoint as ep
import pytest

from rasa_sdk.constants import DEFAULT_ENDPOINTS_PATH


@pytest.mark.parametrize(
    "args, expected",
    [
        ([], DEFAULT_ENDPOINTS_PATH),
        (["--endpoints", "a.yml"], "a.yml"),
    ],
)
def test_arg_parser_endpoints(args, expected):
    parser = ep.create_argument_parser()
    cmdline_args = parser.parse_args(args)
    assert cmdline_args.endpoints == expected

    help_text = parser.format_help()
    assert "--endpoints ENDPOINTS" in help_text
    assert " Configuration file for the assistant as a yml file." in help_text
