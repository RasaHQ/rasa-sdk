from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import pytest
import rasa_sdk.endpoint as ep


def test_arg_parser_actions_params_folder_style():
    parser = ep.create_argument_parser()
    args = ["--actions", "actions/act"]

    with pytest.raises(BaseException) as e:
        parser.parse_args(args)
    if e is not None:
        assert True
    else:
        assert False


def test_arg_parser_actions_params_module_style():
    parser = ep.create_argument_parser()
    args = ["--actions", "actions.act"]
    cmdline_args = parser.parse_args(args)
    assert cmdline_args.actions == "actions.act"
