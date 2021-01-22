"""Web server backend."""
import logging
import json
import asyncio

import aiohttp
from aiohttp import web

from being.serialization import dumps, loads


API_PREFIX = '/api'
"""API route prefix."""

LOGGER = logging.getLogger(__name__)


def file_response_handler(filepath):
    """Create anonymous file response handler for a file."""
    return lambda request: web.FileResponse(filepath)


def json_response_handler(data):
    """Create anonymous JSON response handler function for some data."""
    return lambda request: web.json_response(data, dumps=dumps)


def content_routes(content):
    """Build Rest API routes for content. Wrap content instance in API."""
    routes = web.RouteTableDef()

    @routes.get('/motions')
    async def get_motions(request):
        motions = content.list_motions()
        return web.json_response(motions)

    @routes.get('/motions/{name}')
    async def get_motion_by_name(request):
        name = request.match_info['name']
        spline = content.load_motion(name)
        return web.json_response(spline, dumps=dumps)

    @routes.post('/motions/{name}')
    async def create_motion(request):
        name = request.match_info['name']
        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.Response(
                status=INTERNAL_SERVER_ERROR,
                text='Failed deserializing JSON spline!',
            )

        content.save_motion(spline, name)
        return web.Response()

    @routes.put('/motions/{name}')
    async def update_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.Response(
                status=INTERNAL_SERVER_ERROR,
                text='This motion does not exist!',
            )

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.Response(
                status=INTERNAL_SERVER_ERROR,
                text='Failed deserializing JSON spline!',
            )

        content.save_motion(spline, name)
        return web.Response()

    return routes


def init_api() -> aiohttp.web.Application:
    """Create an application object which handles all API calls."""
    routes = web.RouteTableDef()

    @routes.get('/hello')
    async def say_hello(request: web.Request):
        if 'name' in request.query:
            return web.json_response(
                f"Hello {request.query['name']}"
            )
        else:
            return web.json_response('Hello world')

    @routes.get('/graph')
    async def get_graph(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.get('/blocks')
    async def get_blocks(request: web.Request):
        if 'type' in request.query:
            raise aiohttp.web.HTTPNotImplemented()
        else:
            raise aiohttp.web.HTTPNotImplemented()

    @routes.get('/blocks/{id}')
    async def get_block(request: web.Request):
        return web.json_response(f"TODO: return {request.match_info['id']}")

    @routes.put('/blocks/{id}')
    async def update_block(request: web.Request):
        try:
            data = await request.json()
            # TODO : update block
            return await get_block(request)
        except json.decoder.JSONDecodeError:
            raise aiohttp.web.HTTPBadRequest()

    @routes.get('/connections')
    async def get_connections(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    @routes.get('/state')
    async def get_state(request: web.Request):
        return web.json_response('stopped')

    @routes.put('/state')
    async def set_state(request: web.Request):
        try:
            reqState = await request.json()
            reqState = reqState.upper()

            # TODO : set states
            if reqState == 'RUN':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('RUNNING')
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            elif reqState == 'PAUSE':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('PAUSED')
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            elif reqState == 'STOP':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('STOPPED')
                except Exception as e:
                    return aiohttp.web.HTTPInternalServerError(reson=e)

            else:
                raise aiohttp.web.HTTPBadRequest()

        except json.decoder.JSONDecodeError:
            raise aiohttp.web.HTTPBadRequest()

    @routes.get('/block-network/state')
    async def get_block_network_state(request: web.Request):
        raise aiohttp.web.HTTPNotImplemented()

    api = aiohttp.web.Application()
    api.add_routes(routes)
    return api


def init_web_server(being) -> aiohttp.web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app: Application instance.
    """
    app = aiohttp.web.Application()
    app.router.add_get('/', file_response_handler('static/index.html'))
    app.router.add_static(prefix='/static', path='./static', show_index=True)

    api = init_api()

    #api.add_routes(content_routes(content))

    app.add_subapp(API_PREFIX, init_api())
    #app.router.add_get('/data-stream', handle_web_socket)
    return app


async def run_web_server(app: aiohttp.web.Application):
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

    while True:
        await asyncio.sleep(3600)  # sleep forever


def run_standalone_server():
    app = init_web_server(being=None)
    web.run_app(app)


def run_async_server():
    app = init_web_server(being=None)
    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_web_server(app))
    loop.close()


if __name__ == '__main__':
    # run_standalone_server()
    run_async_server()
