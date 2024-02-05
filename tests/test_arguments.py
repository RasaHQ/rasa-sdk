import rasa_sdk.endpoint as ep


def test_arg_parser_endpoints():
    parser = ep.create_argument_parser()
    args = ["--endpoints", "endpoint.yml"]
    cmdline_args = parser.parse_args(args)
    assert cmdline_args.endpoints == "endpoint.yml"

    help_text = parser.format_help()
    assert "--endpoints ENDPOINTS" in help_text
    assert " Configuration file for tracing as a yml file." in help_text
