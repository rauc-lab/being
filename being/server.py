"""Web server backend."""
import logging
import json
import asyncio

import aiohttp
from aiohttp import web

from being.content import Content
from being.serialization import dumps, loads


API_PREFIX = '/api'
"""API route prefix."""

LOGGER = logging.getLogger(__name__)


def respond_ok():
    """Return with status ok."""
    return web.Response()


def json_response(thing):
    """aiohttp web.json_response but with our custom JSON serialization /
    dumps.
    """
    return web.json_response(thing, dumps=dumps)


def file_response_handler(filepath):
    """Create anonymous file response handler for a file."""
    return lambda request: web.FileResponse(filepath)


def json_response_handler(data):
    """Create anonymous JSON response handler function for some data."""
    return lambda request: json_response(data)


def content_controller(content: Content) -> web.RouteTableDef:
    """Controller for content model. Build Rest API routes. Wrap content
    instance in API.

    Args:
        content: Content model.

    Returns:
        Routes table.
    """
    routes = web.RouteTableDef()

    @routes.get('/motions')
    async def get_all_motions(request):
        motions = content.dict_motions()
        return json_response(motions)

    @routes.get('/motions/{name}')
    async def get_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(f'Motion {name!r} does not exist!')

        spline = content.load_motion(name)
        return json_response(spline)

    @routes.post('/motions/{name}')
    async def create_motion(request):
        name = request.match_info['name']
        if content.motion_exists(name):
            return web.HTTPConflict(f'Motion {name!r} does already exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.HTTPNotAcceptable('Failed deserializing JSON spline!')

        content.save_motion(spline, name)
        return json_response(spline)

    @routes.put('/motions/{name}')
    async def update_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound('This motion does not exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.HTTPNotAcceptable('Failed deserializing JSON spline!')

        content.save_motion(spline, name)
        return json_response(spline)

    @routes.delete('/motions/{name}')
    async def delete_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(f'Motion {name!r} does not exist!')

        content.delete_motion(name)
        return respond_ok()

    return routes


def being_routes(being):
    routes = web.RouteTableDef()

    @routes.get('/graph')
    def foo(request):
        return respond_ok()

    @routes.get('/blocks')
    def foo(request):
        return respond_ok()

    return routes


def init_api() -> web.Application:
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
        raise web.HTTPNotImplemented()

    @routes.get('/blocks')
    async def get_blocks(request: web.Request):
        if 'type' in request.query:
            raise web.HTTPNotImplemented()
        else:
            raise web.HTTPNotImplemented()

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
            raise web.HTTPBadRequest()

    @routes.get('/connections')
    async def get_connections(request: web.Request):
        raise web.HTTPNotImplemented()

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
                    return web.HTTPInternalServerError(reson=e)

            elif reqState == 'PAUSE':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('PAUSED')
                except Exception as e:
                    return web.HTTPInternalServerError(reson=e)

            elif reqState == 'STOP':
                try:
                    print(f'set new state to {reqState}')
                    return web.json_response('STOPPED')
                except Exception as e:
                    return web.HTTPInternalServerError(reson=e)

            else:
                raise web.HTTPBadRequest()

        except json.decoder.JSONDecodeError:
            raise web.HTTPBadRequest()

    @routes.get('/block-network/state')
    async def get_block_network_state(request: web.Request):
        raise web.HTTPNotImplemented()

    api = web.Application()
    api.add_routes(routes)
    return api


def init_web_server(being=None, content=None) -> web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app: Application instance.
    """
    app = web.Application()
    app.router.add_get('/', file_response_handler('static/index.html'))
    app.router.add_static(prefix='/static', path='./static', show_index=True)

    # Rest API
    api = init_api()
    if content:
        api.add_routes(content_controller(content))

    app.add_subapp(API_PREFIX, api)
    #app.router.add_get('/data-stream', handle_web_socket)
    return app


async def run_web_server(app: web.Application):
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
    """Run standalone server for developing purposes."""
    content = Content.single_instance_setdefault()
    app = init_web_server(content=content)
    web.run_app(app)


if __name__ == '__main__':
    run_standalone_server()
