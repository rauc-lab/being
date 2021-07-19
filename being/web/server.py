"""Web server back end."""
import asyncio
import datetime
import functools
import logging
import os
import types

from aiohttp import web
import aiohttp_jinja2
import jinja2

from being import __version__ as BEING_VERSION_NUMBER
from being.behavior import BEHAVIOR_CHANGED
from being.config import  CONFIG
from being.connectables import MessageInput
from being.content import CONTENT_CHANGED, Content
from being.logging import BEING_LOGGERS, get_logger
from being.motors import MOTOR_CHANGED
from being.sensors import Sensor
from being.utils import filter_by_type
from being.web.api import (
    behavior_controllers,
    being_controller,
    content_controller,
    messageify,
    misc_controller,
)
from being.web.web_socket import WebSocket


LOGGER = get_logger(__name__)
"""Server module logger."""


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
        logger.setLevel(logging.INFO)


def patch_sensor_to_web_socket(sensor, ws: WebSocket):
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
    """Initialize and setup Rest-like API sub-app."""
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
    api.add_routes(being_controller(being))

    # Misc functionality
    api.add_routes(misc_controller())

    # Content
    api.add_routes(content_controller(content))
    content.subscribe(CONTENT_CHANGED, lambda: ws.send_json_buffered(content.dict_motions_2()))

    # Patch sensor events
    sensors = list(filter_by_type(being.execOrder, Sensor))
    if len(sensors) > 0:
        sensor = sensors[0]
        patch_sensor_to_web_socket(sensor, ws)

    # Behaviors
    api.add_routes(behavior_controllers(being.behaviors))
    for behavior in being.behaviors:
        behavior.subscribe(BEHAVIOR_CHANGED, ws_emit(behavior))
        content.subscribe(CONTENT_CHANGED, behavior._purge_params)

    # Motors
    for motor in being.motors:
        motor.subscribe(MOTOR_CHANGED, ws_emit(motor))

    wire_being_loggers_to_web_socket(ws)

    return api


def which_year_is_it() -> int:
    """Which year is it now?

    Returns:
        Year number.
    """
    return datetime.date.today().year


def init_web_server(being) -> web.Application:
    """Initialize aiohttp web server application and setup some routes.

    Returns:
        app: Application instance.
    """
    here = os.path.dirname(os.path.abspath(__file__))
    staticDir = os.path.join(here, 'static')
    app = web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.PackageLoader('being.web', 'templates'))
    app.router.add_static(prefix='/static', path=staticDir, show_index=True)
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
            'year': which_year_is_it(),
        }

    app.router.add_routes(routes)
    return app


async def run_web_server(app: web.Application):
    """Run aiohttp web server app asynchronously (new in version 3.0.0).

    Args:
        app (?): Aiohttp web application.
    """
    runner = web.AppRunner(app)
    LOGGER.info('Setting up runner')
    await runner.setup()
    site = web.TCPSite(
        runner,
        host=CONFIG['Web']['HOST'],
        port=CONFIG['Web']['PORT'],
    )
    LOGGER.info(f'Starting site at:\n{site.name}')
    await site.start()

    while True:
        await asyncio.sleep(3600)  # sleep forever
