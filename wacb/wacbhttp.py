#
#    WhatsApp Chat Browser
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#

"""
Classes and functions related to the HTTP server.
"""

import threading
import http.server

class WacbHttpRequestHandler(http.server.BaseHTTPRequestHandler):
    """
    HTTP request handler. Delegates to a callback class.
    """

    # Pylint complains "number of parameters was 3 in base class and is
    # now 3 in overriding method." Huh?
    # pylint: disable=arguments-differ
    def log_message(self, fmt, *args):
        pass

    def do_GET(self):
        httpCode, httpHeaders = self.server.callback.getHttpHeaders(self.path)
        self.send_response(httpCode)
        if httpHeaders:
            for header, value in httpHeaders.items():
                self.send_header(header, value)
        self.end_headers()
        if httpCode == 200:
            self.server.callback.getFile(self.path, self.wfile)

class WacbHttpServer(http.server.ThreadingHTTPServer):
    """
    Wrapper for the standard Python HTTP server.
    """

    def __init__(self, manager, address, callback):
        self.manager = manager
        self.callback = callback
        super().__init__(address,  WacbHttpRequestHandler)

    def __del__(self):
        self.manager.stop()

class WacbHttpServerManager():
    """
    Wrapper to start the HTTP server in a separate thread.
    """

    def __init__(self, callback):
        self.thread = None
        self.server = None
        self.callback = callback
        self.config = {}

    def __del__(self):
        self.stop()

    def configure(self, configData):
        self.config = configData

    def start(self):
        hostName = self.config["hostName"] if "hostName" in self.config else "localhost"
        portNumber = self.config["portNumber"] if "portNumber" in self.config else 0
        self.server = WacbHttpServer(self, (hostName, portNumber), self.callback)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server = None
        if self.thread is not None:
            self.thread.join()
            self.thread = None

    @property
    def name(self):
        return self.server.server_name if self.server else None

    @property
    def port(self):
        return self.server.server_port if self.server else None

    @property
    def url(self):
        if not self.server:
            return None
        return "http://{0}:{1}/".format(self.config["hostName"], self.port)
