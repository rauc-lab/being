from aiohttp import web

from being.serialization import dumps


def respond_ok():
    """Return with status ok."""
    return web.Response()


def json_response(obj=None):
    """aiohttp web.json_response but with our custom JSON serialization dumps.

    Args:
        obj: Object to JSON serialize and pack in a response.
    """
    if obj is None:
        obj = {}

    return web.json_response(obj, dumps=dumps)


def file_response_handler(filepath):
    """Create anonymous file response handler for a file."""
    return lambda request: web.FileResponse(filepath)


def json_response_handler(data):
    """Create anonymous JSON response handler function for some data."""
    return lambda request: json_response(data)