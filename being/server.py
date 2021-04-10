"""Web server back end."""
import asyncio
import json
import logging
import math
import os
import types
from typing import ForwardRef

from aiohttp import web
from scipy.interpolate import BPoly


from being import ROOT_DIR
from being.behavior import BEHAVIOR_CHANGED, State
from being.connectables import MessageInput
from being.content import CONTENT_CHANGED, Content
from being.logging import BEING_LOGGERS
from being.logging import get_logger
from being.sensors import Sensor
from being.serialization import dumps, loads, spline_from_dict
from being.spline import fit_spline
from being.utils import any_item
from being.utils import filter_by_type
from being.web_socket import WebSocket


LOGGER = get_logger(__name__)
"""Server module logger."""

Being = ForwardRef('Being')


def resolve_path(path: str) -> str:
    """Resolve path relative to current root directory.

    Args:
        path: Path to resolve.

    Returns:
        Absolute path.
    """
    # TODO(atheler): Dirty hack but did not find a way to serve the static
    # directory via aiohttp. Tried moving static/ -> being/static/, pkgutil,
    # include_package_data, ...
    #
    # Some links:
    #   - https://stackoverflow.com/questions/6028000/how-to-read-a-static-file-from-inside-a-python-package
    #   - https://setuptools.readthedocs.io/en/latest/userguide/datafiles.html
    # ...
    return os.path.join(ROOT_DIR, path)


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

    @routes.get('/motions2')
    async def get_all_motions_2(request):
        return json_response(content.dict_motions_2())

    @routes.get('/motions/{name}')
    async def get_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        spline = content.load_motion(name)
        return json_response(spline)

    @routes.post('/motions')
    async def create_motion(request):
        name = content.find_free_name('Untitled')
        spline = BPoly([[0], [0], [0], [0]], [0., 1.])
        content.save_motion(spline, name)
        return json_response(spline)

    @routes.put('/motions/{name}')
    async def update_motion(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text='This motion does not exist!')

        if 'rename' in request.query:
            if not content.motion_exists(name):
                return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

            newName = request.query['rename']
            if content.motion_exists(newName):
                return web.HTTPNotAcceptable(text=f'Another file with the same name {name} already exists!')

            content.rename_motion(name, newName)
            return json_response(content.load_motion(newName))

        try:
            spline = await request.json(loads=loads)
            content.save_motion(spline, name)
            return json_response(content.load_motion(name))
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON spline!')
        except:
            return web.HTTPError(text='Saving spline failed!')

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
    for nr, mp in enumerate(being.motionPlayers):
        input_ = any_item(mp.output.outgoingConnections)
        motor = input_.owner
        yield {
            'id': nr,
            'setpointValueIndex': being.valueOutputs.index(mp.output),
            'actualValueIndex': being.valueOutputs.index(motor.output),
            'length': motor.length,
        }


def being_controller(being: Being) -> web.RouteTableDef:
    """API routes for being object.

    Args:
        being: Being instance to wrap up in API.
    """
    routes = web.RouteTableDef()

    @routes.get('/motors')
    async def get_motors(request):
        """Inform front end of available motion players / motors."""
        infos = list(serialize_motion_players(being))
        return json_response(infos)

    @routes.post('/motors/{id}/play')
    async def start_spline_playback(request):
        """Start spline playback for a received spline from front end."""
        being.pause_behaviors()
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            dct = await request.json()
            spline = spline_from_dict(dct['spline'])
            startTime = mp.play_spline(spline, loop=dct['loop'], offset=dct['offset'])
            return json_response({
                'startTime': startTime,
            })
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Could not parse spline!')
        except ValueError as err:
            LOGGER.error(err)
            LOGGER.debug('id: %d', id)
            LOGGER.debug('dct: %s', dct)
            return web.HTTPBadRequest(text=f'Something went wrong with the spline. Raw data was: {dct}!')

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
        """Stop all spline playbacks aka. Stop all motion players."""
        for mp in being.motionPlayers:
            mp.stop()

        return respond_ok()

    @routes.put('/motors/{id}/livePreview')
    async def live_preview(request):
        """Live preview of position value for motor."""
        being.pause_behaviors()
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            data = await request.json()
            pos = data['position']
            if pos is None or not math.isfinite(pos):
                return web.HTTPBadRequest(text=f'Invalid value {pos} for live preview!')

            mp.live_preview(data['position'])
            return json_response()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Could not parse spline!')

    @routes.put('/motors/disenable')
    def disenable_drives(request):
        being.pause_behaviors()
        if being.network:
            being.network.engage_drives()

        return respond_ok()

    @routes.put('/motors/enable')
    def enable_drives(request):
        for motor in being.motors:
            motor._update_state()

        if being.network:
            being.network.enable_drives()

        return respond_ok()

    return routes


def behavior_controller(behavior) -> web.RouteTableDef:
    # TODO: For now we only support 1x behavior instance. Needs to be expanded for the future
    routes = web.RouteTableDef()

    @routes.get('/behavior/states')
    def get_states(request):
        stateNames = list(State.__members__)
        return json_response(stateNames)

    @routes.get('/behavior')
    def get_info(request):
        return json_response(behavior.infos())

    @routes.put('/behavior/toggle_playback')
    def toggle_playback(request):
        if behavior.active:
            behavior.pause()
        else:
            behavior.play()

        return json_response(behavior.infos())

    @routes.get('/behavior/params')
    def get_params(request):
        return json_response(behavior.params)

    @routes.put('/behavior/params')
    async def set_params(request):
        try:
            params = await request.json()
            behavior.params = params
            return json_response(behavior.infos())
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text=f'Failed deserializing JSON behavior params!')

    return routes


def misc_controller() -> web.RouteTableDef:
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


def wire_being_loggers_to_web_socket(ws: WebSocket):
    """Add custom logging handler to all being loggers which emits log records
    via web socket to the front end.

    Args:
        ws: Web socket.
    """
    class WsHandler(logging.Handler):
        def emit(self, record):
            ws.send_json_buffered({
                'type': 'log',
                'level': record.levelno,
                'name': record.name,
                'message': self.format(record),
            })

    handler = WsHandler()
    for logger in BEING_LOGGERS:
        logger.addHandler(handler)


def patch_sensor_to_web_socket(sensor, ws):
    """Route sensor output messages to web socket."""
    # MessageOutput can only connect to an instance of MessageInput. No
    # subclassing possible. Let us monkey patch the push method of a dummy
    # instance of MessageInput instead.
    # TODO(atheler): For the future, and more sensors, probably best to
    # introduce some kind of phantom block with multiple message inputs. Or
    # adding this functionality to the being instance itself.
    dummy = MessageInput()

    def push(self, message):
        ws.send_json_buffered({
            'type': 'sensor-message',
            'event': message,
        })

    dummy.push = types.MethodType(push, dummy)
    sensor.output.connect(dummy)


def init_api(being, ws: WebSocket) -> web.Application:
    """Initialize and setup Rest-like API subapp."""
    content = Content.single_instance_setdefault()
    api = web.Application()
    api.add_routes(misc_controller())
    api.add_routes(content_controller(content))

    # Content
    content.subscribe(CONTENT_CHANGED, lambda: ws.send_json_buffered(content.dict_motions_2()))

    # Behavior
    if len(being.behaviors) >= 1:
        behavior = being.behaviors[0]
        api.add_routes(behavior_controller(behavior))
        behavior.subscribe(BEHAVIOR_CHANGED, lambda: ws.send_json_buffered(behavior.infos()))
        content.subscribe(CONTENT_CHANGED, behavior._purge_params)

    # Being
    api.add_routes(being_controller(being))

    logging.basicConfig(level=20)
    wire_being_loggers_to_web_socket(ws)

    # Patch sensor events
    sensors = list(filter_by_type(being.execOrder, Sensor))
    if len(sensors) > 0:
        sensor = sensors[0]
        patch_sensor_to_web_socket(sensor, ws)

    return api


def init_web_server() -> web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app: Application instance.
    """
    app = web.Application()
    app.router.add_static(
        prefix='/static',
        path=resolve_path('static'),
        show_index=True,
    )
    app.router.add_get(
        '/favicon.ico',
        file_response_handler(resolve_path('static/favicon.ico')),
    )
    app.router.add_get(
        '/',
        file_response_handler(resolve_path('static/index.html')),
    )
    app.router.add_get(
        '/being',
        file_response_handler(resolve_path('static/being.html')),
    )
    app.router.add_get(
        '/web-socket-test',
        file_response_handler(resolve_path('static/web-socket-test.html')),
    )
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
