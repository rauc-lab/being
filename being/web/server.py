"""Web server back end."""
import asyncio
import datetime
import logging
import os
import types

from aiohttp import web
import aiohttp_jinja2
import jinja2

from being import __version__ as BEING_VERSION_NUMBER
from being.behavior import BEHAVIOR_CHANGED
from being.being import Being
from being.configuration import CONFIG
from being.connectables import MessageInput
from being.content import CONTENT_CHANGED, Content
from being.logging import BEING_LOGGER, get_logger
from being.motors.definitions import MotorEvent
from being.params import MotionSelection
from being.sensors import Sensor
from being.utils import filter_by_type
from being.web.api import (
    behavior_routes,
    being_routes,
    content_routes,
    messageify,
    misc_routes,
    motion_player_routes,
    motor_routes,
    params_routes,
)
from being.web.web_socket import WebSocket


# Look before you leap
API_PREFIX = CONFIG['Web']['API_PREFIX']
WEB_SOCKET_ADDRESS = CONFIG['Web']['WEB_SOCKET_ADDRESS']
INTERVAL = CONFIG['General']['INTERVAL']
WEB_INTERVAL = CONFIG['Web']['INTERVAL']


LOGGER = get_logger(name=__name__, parent=None)


def wire_being_loggers_to_web_socket(ws: WebSocket):
    """Add custom logging handler to all being loggers which emits log records
    via web socket to the front end.

    Args:
        ws: Web socket.
    """
    class WsHandler(logging.Handler):
        def emit(self, record):
            ws.send_json_buffered(record)

    handler = WsHandler()
    BEING_LOGGER.addHandler(handler)


def patch_sensor_to_web_socket(sensor, ws: WebSocket):
    """Route sensor output messages to web socket."""
    # MessageOutput can only connect to an instance of MessageInput. No
    # subclassing possible. Let us monkey patch the push method of a dummy
    # instance of MessageInput instead.
    # Todo(atheler): For the future, and more sensors, probably best to
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


def init_api(being: Being, ws: WebSocket) -> web.Application:
    """Initialize and setup sub-app for API. Some actions affect other
    components which get updated via the web socket.

    Args:
        being: Being instance.
        ws: Web socket.

    Returns:
        aiohttp API sub.application.
    """
    content = Content.single_instance_setdefault()
    api = web.Application()


    def ws_emit(obj):
        """Function factory for creating callable sender task to emit the
        current state of an object via the web socket connection. Used for the
        PubSub pattern further down to register subscribers.

        Originally lambda's were in place for this job but that led to a nasty
        false reference bug when iterating over e.g. multiple motors.

        The bug can be basically recreated with this:

            >>> callbacks = []
            ... for obj in range(5):
            ...     callbacks.append(lambda: obj)
            ...
            ... for func in callbacks:
            ...     print(func())
            4
            4
            4
            4
            4

        All the lambda point to the name `obj` which changes during the
        iteration. Possible workarounds:
          - Using functools.partial
          - Intermediate function for freezing the scope.

        The decision fell on the latter in order to protect posterity.
        """
        return lambda: ws.send_json_buffered(messageify(obj))

    # Being
    api.add_routes(being_routes(being))

    # Misc functionality
    api.add_routes(misc_routes())

    # Content
    api.add_routes(content_routes(content))
    content.subscribe(CONTENT_CHANGED, lambda: ws.send_json_buffered(content.forge_message()))
    for motionSelection in filter_by_type(being.params, MotionSelection):
        content.subscribe(CONTENT_CHANGED, motionSelection.on_content_changed)

    # Patch sensor events
    sensors = list(filter_by_type(being.execOrder, Sensor))
    if len(sensors) > 0:
        sensor = sensors[0]
        patch_sensor_to_web_socket(sensor, ws)

    # Behaviors
    api.add_routes(behavior_routes(being.behaviors))
    for behavior in being.behaviors:
        behavior.subscribe(BEHAVIOR_CHANGED, ws_emit(behavior))
        content.subscribe(CONTENT_CHANGED, behavior._purge_params)

    # Motion players
    api.add_routes(motion_player_routes(being.motionPlayers, being.behaviors))

    # Motors
    api.add_routes(motor_routes(being))

    def ws_motor_error_notification(motor):
        return lambda msg: ws.send_json_buffered({
            'type': 'motor-error',
            'motor': motor,
            'message': msg,
        })

    for motor in being.motors:
        motor.subscribe(MotorEvent.STATE_CHANGED, ws_emit(motor))
        motor.subscribe(MotorEvent.HOMING_CHANGED, ws_emit(motor))
        motor.subscribe(MotorEvent.ERROR, ws_motor_error_notification(motor))

    api.add_routes(params_routes(being.params))

    wire_being_loggers_to_web_socket(ws)

    return api


def which_year_is_it() -> int:
    """Which year is it now?

    Returns:
        Year number.
    """
    return datetime.date.today().year


def init_web_server(being: Being, ws: WebSocket) -> web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Args:
        being: Being instance.
        ws: Web socket

    Returns:
        app: Application instance.
    """
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('being.web', 'templates'))

    # Web socket
    app.router.add_get(WEB_SOCKET_ADDRESS, ws.handle_new_connection)

    # Signals
    app.on_startup.append(ws.start_broker)
    app.on_shutdown.append(ws.stop_broker)
    app.on_shutdown.append(ws.close_all_connections)

    # Static directory
    here = os.path.dirname(os.path.abspath(__file__))
    staticDir = os.path.join(here, 'static')
    app.router.add_static(prefix='/static', path=staticDir, show_index=True)

    # Routes
    routes = web.RouteTableDef()

    @routes.get('/favicon.ico')
    async def get_favicon(request):
        return web.FileResponse(os.path.join(staticDir, 'favicon.ico'))

    @routes.get('/')
    @aiohttp_jinja2.template('index.html')
    async def get_index(request):
        return {
            'version': BEING_VERSION_NUMBER,
            'behaviors': being.behaviors,
            'motionPlayers': being.motionPlayers,
            'year': which_year_is_it(),
            'hasParams': bool(being.params),
        }

    app.router.add_routes(routes)

    # API
    api = init_api(being, ws)
    app.add_subapp(API_PREFIX, api)

    return app


async def run_web_server(app: web.Application):
    """Run aiohttp web server app asynchronously (new in version 3.0.0).

    Args:
        app: Aiohttp web application to run.

    References:
        `Application runners <https://docs.aiohttp.org/en/stable/web_advanced.html#aiohttp-web-app-runners>`_
    """
    runner = web.AppRunner(app, handle_signals=True)
    LOGGER.info('Setting up runner')
    await runner.setup()
    site = web.TCPSite(
        runner,
        host=CONFIG['Web']['HOST'],
        port=CONFIG['Web']['PORT'],
    )
    LOGGER.info(f'Starting site at:\n{site.name}')
    await site.start()

    try:
        while True:
            await asyncio.sleep(3600)  # sleep forever
    finally:
        await runner.cleanup()
