"""Web server back end."""
import logging
import json
import asyncio

from aiohttp import web

from being.content import Content
from being.serialization import dumps, loads, spline_from_dict
from being.spline import fit_spline
from being.utils import random_name, empty_spline, any_item


API_PREFIX = '/api'
"""API route prefix."""

WEB_SOCKET_ADDRESS = '/stream'
"""Web socket URL."""

LOGGER = logging.getLogger(__name__)
"""Server module logger."""


def respond_ok():
    """Return with status ok."""
    return web.Response()


def json_response(thing=None):
    """aiohttp web.json_response but with our custom JSON serialization /
    dumps.
    """
    if thing is None:
        thing = {}

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
        return json_response(content.dict_motions())

    @routes.get('/motions/{name}')
    async def get_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        spline = content.load_motion(name)
        return json_response(spline)

    @routes.post('/motions')
    async def create_motion(request):

        rnd_name = random_name()
        while content.motion_exists(rnd_name):
            rnd_name = random_name()

        spline = empty_spline()

        content.save_motion(spline, rnd_name)
        return json_response(spline)

    @routes.put('/motions/{name}')
    async def update_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text='This motion does not exist!')

        try:
            if "rename" in request.query:
                new_name = request.query["rename"]
                if content.motion_exists(new_name):
                    return web.HTTPNotAcceptable(text="Another file with the same name already exists")
                try:
                    content.rename_motion(name, new_name)
                    return json_response(content.load_motion(new_name))
                except:
                    return web.HTTPError(text="Renaming failed!")

            else:
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

    @routes.post('/motions/{name}')
    async def duplicate_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        content.duplicate_motion(name)
        return respond_ok()

    return routes


def serialize_motion_players(being):
    """Return list of motion player / motors informations."""
    ret = []
    for nr, mp in enumerate(being.motionPlayers):
        input_ = any_item(mp.output.outgoingConnections)
        motor = input_.owner
        dct = {
            "id": nr,
            "setpointValueIndex": being.valueOutputs.index(mp.output),
            "actualValueIndex": being.valueOutputs.index(motor.output),
        }
        ret.append(dct)

    return ret


def being_controller(being) -> web.RouteTableDef:
    """API routes for being object."""
    routes = web.RouteTableDef()

    @routes.get('/motors')
    async def get_motors(request):
        """Inform front end of available motion players / motors."""
        return json_response(serialize_motion_players(being))


    @routes.post('/motors/{id}/play')
    async def start_spline_playback(request):
        """Start spline playback for a received spline from front end."""
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            dct = await request.json()
            spline = spline_from_dict(dct['spline'])
            return json_response({
                'startTime': mp.play_spline(spline, loop=dct['loop'], offset=dct['offset']),
            })
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Could not parse spline!')
        except ValueError as err:
            LOGGER.error(err)
            LOGGER.debug('id: %d', id)
            LOGGER.debug('dct: %s', dct)
            return web.HTTPBadRequest(text='fSomething went wrong with the spline. Raw data was: {dct}!')


    @routes.post('/motors/{id}/stop')
    async def stop_spline_playback(request):
        """Stop spline playback."""
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            mp.stop()
            return respond_ok()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')


    @routes.post('/motors/stop')
    async def stop_all_spline_playbacks(request):
        """Stop all spline playbacks aka. stop all motion players."""
        for mp in being.motionPlayers:
            mp.stop()

        return respond_ok()


    @routes.put('/motors/{id}/livePreview')
    async def live_preview(request):
        """Live preview of position value for motor."""
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            data = await request.json()
            mp.live_preview(data['position'])
            return json_response()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Could not parse spline!')


    @routes.put("/motors/disenable")
    def disenable_drives(request):
        if being.network:
            being.network.engage_drives()

        return respond_ok()

    @routes.put("/motors/enable")
    def enable_drives(request):
        for motor in being.motors:
            motor._update_state()

        if being.network:
            being.network.enable_drives()

        return respond_ok()

    return routes


def misc_controller():
    """All other APIs which are not directly related to being, content,
    etc...
    """
    routes = web.RouteTableDef()

    @routes.post('/fit_spline')
    async def convert_trajectory(request):
        """Convert a trajectory array to a spline."""
        try:
            trajectory = await request.json()
            spline = fit_spline(trajectory)
            return json_response(spline)
        except ValueError:
            return web.HTTPBadRequest(text='Wrong trajectory data format. Has to be 2d!')

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
    app.router.add_get('/favicon.ico', file_response_handler('static/favicon.ico'))

    # Rest API
    api = web.Application()
    api.add_routes(misc_controller())
    if being:
        api.add_routes(being_controller(being))

    if content:
        api.add_routes(content_controller(content))

    app.add_subapp(API_PREFIX, api)
    # app.router.add_get('/data-stream', handle_web_socket)
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
    # Run server with dummy being
    from being.being import awake
    from being.motion_player import MotionPlayer
    from being.motor import DummyMotor

    blocks = [
        MotionPlayer() | DummyMotor(),
        MotionPlayer() | DummyMotor(),
    ]

    awake(*blocks)
