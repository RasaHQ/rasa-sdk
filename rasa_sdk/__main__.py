from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from rasa_sdk import utils
from rasa_sdk.endpoint import create_argument_parser, run


def main_from_args(args):
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("matplotlib").setLevel(logging.WARN)

    utils.configure_colored_logging(args.loglevel)

    run(args.actions, args.port, args.cors)


def main():
    # Running as standalone python application
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()

    main_from_args(cmdline_args)


if __name__ == "__main__":
    main()
