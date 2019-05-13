from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from rasa_sdk import utils
from rasa_sdk.endpoint import create_argument_parser, run


def main():
    # Running as standalone python application
    arg_parser = create_argument_parser()
    cmdline_args = arg_parser.parse_args()

    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("matplotlib").setLevel(logging.WARN)

    utils.configure_colored_logging(cmdline_args.loglevel)

    run(cmdline_args.actions, cmdline_args.port, cmdline_args.cors)


if __name__ == "__main__":
    main()
