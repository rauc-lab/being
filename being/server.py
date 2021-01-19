"""Web server backend."""
import asyncio
import logging
import json

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

    routes = web.RouteTableDef()
    apiPrefix = '/api/'

    @routes.get(apiPrefix + 'hello')
    async def say_hello(request: web.Request):
        if 'name' in request.query:
            return web.json_response(
                f"Hello {request.query['name']}"
            )
        else:
            return web.json_response("Hello world")

    @routes.get(apiPrefix + 'graph')
    async def get_graph(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.get(apiPrefix + 'blocks')
    async def get_blocks(request: web.Request):
        if 'type' in request.query:
            raise aiohttp.web.HTTPNotImplemented()
        else:
            raise aiohttp.web.HTTPNotImplemented()

    @routes.get(apiPrefix + 'blocks/{id}')
    async def get_block(request: web.Request):
        return web.json_response(f"TODO: return {request.match_info['id']}")

    @routes.put(apiPrefix + 'blocks/{id}')
    async def update_block(request: web.Request):
        try:
            data = await request.json()
            # TODO : update block
            return await get_block(request)
        except json.decoder.JSONDecodeError:
            raise aiohttp.web.HTTPBadRequest()

    @routes.get(apiPrefix + 'connections')
    async def get_connections(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.get(apiPrefix + 'state')
    async def get_state(request: web.Request):
        return web.json_response('stopped')

    @routes.put(apiPrefix + 'state')
    async def set_state(request: web.Request):
        try:
            reqState = await request.json()
            reqState = reqState.upper()

            # TODO : set states
            if reqState == 'RUN':
                try:
                    print(f"set new state to {reqState}")
                    return web.json_response("RUNNING")
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            elif reqState == 'PAUSE':
                try:
                    print(f"set new state to {reqState}")
                    return web.json_response("PAUSED")
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            elif reqState == 'STOP':
                try:
                    print(f"set new state to {reqState}")
                    return web.json_response("STOPPED")
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            else:
                raise aiohttp.web.HTTPBadRequest()

        except json.decoder.JSONDecodeError:
            raise aiohttp.web.HTTPBadRequest()

    @routes.get(apiPrefix + 'motions')
    async def get_motions(request: web.Request):
        return web.json_response(
            {
                "demo.json": "",
                "demo2.json": "Test",
            },
        )

    @routes.post(apiPrefix + 'motions')
    async def post_motion(request: web.Request):
        try:
            data = await request.post()
            filename = list(data.keys())[0]
            if filename:
                # TODO: create new motion object & sanity check
                return web.json_response(data)
            else:
                return aiohttp.web.HTTPBadRequest()
        except Exception as e:
            return aiohttp.web.HTTPInternalServerError(reson=e)

    @routes.get(apiPrefix + 'motions/{name}')
    async def get_motion(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.put(apiPrefix + 'motions/{name}')
    async def put_motion(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.delete(apiPrefix + 'motions/{name}')
    async def delete_motion(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.get(apiPrefix + 'block-network/state')
    async def get_block_network_state(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    app.add_routes(routes)

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
