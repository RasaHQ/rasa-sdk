from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import logging

from gevent.pywsgi import WSGIServer

from rasa_core_sdk import utils
from rasa_core_sdk.endpoint import endpoint_app

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    utils.configure_colored_logging("DEBUG")

    app = endpoint_app(action_package_name="myactions")

    http_server = WSGIServer(('0.0.0.0', 5055), app)

    http_server.start()
    logger.info("Action endpoint is up and running on "
                "http://{}:{}.".format(
            http_server.address[0], http_server.address[1]))

    http_server.serve_forever()
