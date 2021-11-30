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

# Note: Do not use lambda function as response factories! Leads to errors under Windows because the
# IocpProactor proactor does not accept non-async lambda functions.
#
# Excerpt:
#     raise TypeError("Only async functions are allowed as web-handlers "
# TypeError: Only async functions are allowed as web-handlers , got <function file_response_handler.<locals>.<lambda> at 0x000001A40BF45CA0>
# 
#def file_response_handler(filepath):
#    """Create anonymous file response handler for a file."""
#    return lambda request: web.FileResponse(filepath)
#
#
#def json_response_handler(data):
#    """Create anonymous JSON response handler function for some data."""
#    return lambda request: json_response(data)
