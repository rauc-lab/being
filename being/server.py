"""Web server backend."""
import logging
import json
import asyncio
from collections import OrderedDict, defaultdict

from aiohttp import web

from being.content import Content
from being.serialization import dumps, loads


API_PREFIX = '/api'
"""API route prefix."""

LOGGER = logging.getLogger(__name__)
"""Server module logger."""


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
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        spline = content.load_motion(name)
        return json_response(spline)

    @routes.post('/motions/{name}')
    async def create_motion(request):
        name = request.match_info['name']
        if content.motion_exists(name):
            return web.HTTPConflict(text=f'Motion {name!r} does already exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON spline!')

        content.save_motion(spline, name)
        return json_response(spline)

    @routes.put('/motions/{name}')
    async def update_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text='This motion does not exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError as err:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON spline!')

        content.save_motion(spline, name)
        return json_response(spline)

    @routes.delete('/motions/{name}')
    async def delete_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        content.delete_motion(name)
        return respond_ok()

    return routes


def init_web_server(being=None, content=None) -> web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app: Application instance.
    """
    if content is None:
        content = Content.single_instance_setdefault()

    app = web.Application()
    app.router.add_static(prefix='/static', path='./static', show_index=True)

    # Pages
    app.router.add_get('/', file_response_handler('static/index.html'))
    app.router.add_get('/spline-editor', file_response_handler('static/spline-editor.html'))
    app.router.add_get('/live-plotter', file_response_handler('static/live-plotter.html'))

    # Rest API
    api = web.Application()
    # TODO: Being API
    if being:
        pass

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


if __name__ == '__main__':
    content = Content.single_instance_setdefault()
    app = init_web_server(content=content)
    web.run_app(app)
