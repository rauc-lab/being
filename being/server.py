"""Web server backend."""
import asyncio
import logging

import aiohttp
from aiohttp import web


LOGGER = logging.getLogger(__name__)


def file_response_handler(filepath):
    """Create file response handler function."""
    def handle_request(request):
        return web.FileResponse(filepath)

    return handle_request


def json_response_handler(data):
    """Create JSON response handler function."""
    def handle_request(request):
        return web.json_response(data)

    return handle_request


async def handle_web_socket(request):
    """Web socket connection handler."""
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    print('New web socket connection')

    await ws.send_json('Hello')
    async for msg in ws:
        print('Received', msg)
        if msg.type == aiohttp.WSMsgType.TEXT:
            if msg.data == 'close':
                await ws.close()
            else:
                await ws.send_str(msg.data + '/answer')

        elif msg.type == aiohttp.WSMsgType.ERROR:
            print('ws connection closed with exception %s' % ws.exception())

    print('websocket connection closed')
    return ws


def init_web_server():
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app (?): Application instance.
    """
    app = aiohttp.web.Application()
    app.router.add_get('/', file_response_handler('static/index.html'))
    app.router.add_static(prefix='/static', path='./static', show_index=True)

    # Routes
    # GET -> app.router.add_get(url, handler)
    # PUT -> app.router.add_put(url, handler)
    # POST -> app.router.add_post(url, handler)
    # ...

    # Setup websocket
    app.router.add_get('/data-stream', handle_web_socket)

    return app


async def run_web_server(app):
    """Run aiohttp web server app asynchronously (new in version 3.0.0).

    Args:
        app (?): Aiohttp web application.
    """
    runner = web.AppRunner(app)
    LOGGER.info('Setting up runner')
    await runner.setup()
    site = web.TCPSite(runner)
    LOGGER.info(f'Starting site at:\n{site.name}')
    await site.start()


def run_standalone_server():
    app = init_web_server()
    web.run_app(app)


if __name__ == '__main__':
    run_standalone_server()
