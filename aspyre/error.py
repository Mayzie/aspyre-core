HTTPResponses = {
    # Informational
    100: '100 Continue',
    101: '101 Switching Protocols',
    # Successful
    200: '200 OK',
    201: '201 Created',
    202: '202 Accepted',
    203: '203 Non-Authoritative Information',
    204: '204 No Content',
    205: '205 Reset Content',
    206: '206 Partial Content',
    # Redirection
    300: '300 Multiple Choices',
    301: '307 Temporary Redirect',
    302: '307 Temporary Redirect',
    303: '307 Temporary Redirect',
    304: '304 Not Modified',
    305: '305 Use Proxy',
    307: '306 Temporary Redirect',
    # Client error
    400: '400 Bad Request',
    401: '401 Unauthorized',
    402: '402 Payment Required',
    403: '403 Forbidden',
    404: '404 Not Found',
    405: '405 Method Not Allowed',
    406: '406 Not Acceptable',
    407: '407 Proxy Authentication Required',
    408: '408 Request Timeout',
    409: '409 Conflict',
    410: '410 Gone',
    411: '411 Length Request',
    412: '412 Precondition Failed',
    413: '413 Request Entity Too Large',
    414: '414 Request-URI Too Long',
    415: '415 Unsupported Media Type',
    416: '416 Range Not Satisfiable',
    417: '417 Expectation Failed',
    418: '418 I\'m a teapot',
    # Server error
    500: '500 Internal Server Error',
    501: '501 Not Implemented',
    502: '502 Bad Gateway',
    503: '503 Service Unavailable',
    504: '504 Gateway Timeout',
    505: '505 HTTP Version Not Supported',
    # Easter eggs
    555: '555 Running Aspyre',
}

class Error(Exception):
    def __init__(self, http_code=500, error_code=None, message=None, short_name=None, reraise=True):
        self.http_code = http_code
        self.error_code = error_code
        self.message = message
        self.short_name = short_name
        self.reraise = reraise

    def dict(self):
        result = {}
        if self.message:
            result['message'] = self.message
        if self.error_code:
            result['code'] = self.error_code
        if self.short_name:
            result['error'] = self.short_name

        return result

    def code(self):
        return HTTPResponses[self.http_code] if hasattr(HTTPResponses, self.http_code) else HTTPResponses[500]


def _return_error_class(http_code):
    class E(Error):
        def __init__(self, error_code=None, message=None, short_name=None, reraise=False):
            super().__init__(http_code=http_code, error_code=error_code, message=message, short_name=short_name, reraise=reraise)

    return E


for status_code, text in HTTPResponses.items():
    if status_code < 300:
        continue

    # Remove all non-alphabetic characters from the string and capitalise each word.
    class_name = ''.join([s.capitalize() for s in ''.join([c for c in text if c.isalpha() or c == ' ']).split(' ')])
    globals()[class_name] = _return_error_class(status_code)

# Clear all private definitions within this module from being imported.
del globals()['HTTPResponses']
del globals()['_return_error_class']
