"""Web server back end."""
import os
import asyncio
import logging
import types

from aiohttp import web

from being.behavior import BEHAVIOR_CHANGED
from being.config import  CONFIG
from being.connectables import MessageInput
from being.content import CONTENT_CHANGED, Content
from being.logging import BEING_LOGGERS
from being.logging import get_logger
from being.sensors import Sensor
from being.utils import filter_by_type
from being.web.api import content_controller, being_controller, behavior_controller, misc_controller
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
    here = os.path.dirname(os.path.abspath(__file__))
    staticDir = os.path.join(here, 'static')
    app = web.Application()
    app.router.add_static(prefix='/static', path=staticDir, show_index=True)

    routes = web.RouteTableDef()

    @routes.get('/favicon.ico')
    async def get_favicon(request):
        return web.FileResponse(os.path.join(staticDir, 'favicon.ico'))


    @routes.get('/')
    async def get_index(request):
        return web.FileResponse(os.path.join(staticDir, 'index.html'))


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
