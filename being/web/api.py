"""API calls  and routes for communication with front-end."""
import collections
import functools
import glob
import io
import itertools
import json
import math
import os
import zipfile
from typing import Dict

import numpy as np
from aiohttp import web
from aiohttp.typedefs import MultiDictProxy

from being.behavior import State as BehaviorState, Behavior
from being.being import Being
from being.configs import Config
from being.configuration import CONFIG
from being.connectables import ValueOutput, _ValueContainer
from being.content import CONTENT_CHANGED, Content
from being.curve import Curve
from being.logging import get_logger
from being.motors.blocks import MotorBlock
from being.params import Parameter
from being.serialization import loads
from being.spline import fit_spline
from being.typing import Spline
from being.utils import filter_by_type, update_dict_recursively
from being.web.responses import respond_ok, json_response


LOGGER = get_logger(name=__name__, parent=None)


def messageify(obj) -> collections.OrderedDict:
    """Serialize being objects and wrap them inside a message object.
    In order to differentiate between the message about an `object` and the
    `object` itself.

    Args:
        obj: Some being object to send.

    Returns:
        JSON serializable OrderedDict.
    """
    if isinstance(obj, Behavior):
        return collections.OrderedDict([
            ('type', 'behavior-update'),
            ('behavior', obj),
        ])

    if isinstance(obj, MotorBlock):
        return collections.OrderedDict([
            ('type', 'motor-update'),
            ('motor', obj),
        ])

    if isinstance(obj, list) and all(isinstance(o, MotorBlock) for o in obj):
        return collections.OrderedDict([
            ('type', 'motor-updates'),
            ('motors', obj),
        ])

    raise ValueError(f'Do not know how to create message for {obj}!')


def content_routes(content: Content) -> web.RouteTableDef:
    """Controller for content model. Build Rest API routes. Wrap content
    instance in API.

    Args:
        content: Being content instance.

    Returns:
        Routes table for API app.
    """
    routes = web.RouteTableDef()

    @routes.get('/curves')
    async def get_curves(request):
        """Get all current curves."""
        return json_response(content.forge_message())

    @routes.get('/curves/{name}')
    async def get_curve(request):
        """Get single curve by name."""
        name = request.match_info['name']
        if not content.curve_exists(name):
            return web.HTTPNotFound(text=f'Curve {name!r} does not exist!')

        spline = content.load_curve(name)
        return json_response(spline)

    @routes.post('/curves/{name}')
    async def create_curve(request):
        """Create a new curve."""
        name = request.match_info['name']
        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON curve!')

        content.save_curve(name, spline)
        return json_response()

    @routes.put('/curves/{name}')
    async def update_curve(request):
        """Update a existing curve."""
        name = request.match_info['name']
        if not content.curve_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON curve!')

        content.save_curve(name, spline)
        return json_response()

    @routes.delete('/curves/{name}')
    async def delete_curve(request):
        """Delete a curve."""
        name = request.match_info['name']
        if not content.curve_exists(name):
            return web.HTTPNotFound(text=f'Curve {name!r} does not exist!')

        content.delete_curve(name)
        return json_response()

    @routes.put('/rename_curve')
    async def rename_curve(request):
        instructions = await request.json()
        oldName = instructions['oldName']
        newName = instructions['newName']
        content.rename_curve(oldName, newName)
        return json_response()

    @routes.get('/find-free-name')
    async def find_free_name(request):
        """Find an available name."""
        return json_response(content.find_free_name())

    @routes.get('/find-free-name/{wishName}')
    async def find_free_name_wish_name(request):
        wishName = request.match_info['wishName']
        return json_response(content.find_free_name(wishName=wishName))

    @routes.get('/download-zipped-curves')
    async def download_zipped_curves(request):
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as zf:
            for fp in glob.glob(content.directory + '/*.json'):
                zf.write(fp)

        stream.seek(0)

        return web.Response(
            body=stream,
            content_type='application/zip'
        )

    def pluck_files(dct: MultiDictProxy) -> tuple:
        """Pluck JSON files (and data) from MultiDictProxy files dct. Also open
        up zip files if any.

        Args:
            dct: Multi dict proxy from file upload post request.

        Yields:
            File basename and raw data.
        """
        for filefield in dct.values():
            fn = filefield.filename
            if fn.lower().endswith('.zip'):
                with zipfile.ZipFile(filefield.file, 'r') as zf:
                    for fp in zf.namelist():
                        yield fp, zf.read(fp)
            else:
                yield fn, filefield.file.read()

    @routes.post('/upload-curves')
    async def upload_curves(request):
        data = await request.post()

        # Empty upload
        if isinstance(data, bytearray):
            return json_response([{'type': 'error', 'message': 'Nothing uploaded!'}])

        notificationMessages = []
        for fp, data in pluck_files(data):
            if not fp.lower().endswith('.json'):
                notificationMessages.append({'type': 'error', 'message': '%r is not a JSON file!' % fp})
                continue

            try:
                thing = loads(data)
                if not isinstance(thing, Spline.__args__):
                    raise ValueError('is not a spline!')

                fn = os.path.basename(fp)
                with open(os.path.join(content.directory, fn), 'wb') as f:
                    f.write(data)

                notificationMessages.append({'type': 'success', 'message': 'Uploaded file %r' % fp})
            except Exception as err:
                notificationMessages.append({'type': 'error', 'message': '%r %s' % (fp, err)})

        content.publish(CONTENT_CHANGED)
        return json_response(notificationMessages)

    return routes


def serialize_elk_graph(being: Being, skipParamBlocks: bool = True):
    """Serialize being blocks to ELK style graph dict serialization. Used in UI
    for block network visualization.

    Args:
        being: Being instance.
        skipParamBlocks (optional): If to skip all Params blocks to reduce
            clutter. True by default.

    Returns:
        Dict based graph representation compatible with ELK JS lib.

    Note:
        Why yet another graph serialization? Because of edge connection type and
        double edges. These things do not matter for the execOrder, but they do
        for the block diagram.
    """
    # ELK style graph object
    elkGraph = collections.OrderedDict([
        ('id', 'root'),
        ('children', []),
        ('edges', []),
    ])
    queue = collections.deque(being.execOrder)
    visited = set()
    edgeIdCounter = itertools.count()
    while queue:
        block = queue.popleft()
        if block in visited:
            continue

        if skipParamBlocks and isinstance(block, Parameter):
            continue

        visited.add(block)
        elkGraph['children'].append({
            'id': block.id,
            'name': block.name,
        })

        for output in block.outputs:
            if isinstance(output, _ValueContainer):
                connectionType = 'value'
                index = being.valueOutputs.index(output)
            else:
                connectionType = 'message'
                index = being.messageOutputs.index(output)

            for input_ in output.outgoingConnections:
                if input_.owner and input_.owner is not block:
                    elkGraph['edges'].append({
                        'id': 'edge %d' % next(edgeIdCounter),
                        'index': index,
                        'connectionType': connectionType,
                        'sources': [block.id],
                        'targets': [input_.owner.id],
                    })

    return elkGraph


def being_routes(being: Being) -> web.RouteTableDef:
    """API routes for being object.

    Args:
        being: Being instance to wrap up in API.

    Returns:
        Routes table for API app.
    """
    routes = web.RouteTableDef()

    blockLookup = { block.id: block for block in being.execOrder }

    @routes.get('/blocks')
    async def get_blocks(request):
        return json_response(blockLookup)

    @routes.get('/blocks/{id}')
    async def get_block(request):
        id = int(request.match_info['id'])
        try:
            block = blockLookup[id]
            return json_response(block)
        except KeyError:
            return web.HTTPBadRequest(text=f'Unknown block with id {id}!')

        return json_response(blockLookup)

    @routes.get('/blocks/{id}/index_of_value_outputs')
    async def get_index_of_value_outputs(request):
        id = int(request.match_info['id'])
        try:
            block = blockLookup[id]
            return json_response([
                being.valueOutputs.index(out)
                for out in filter_by_type(block.outputs, ValueOutput)
            ])
        except KeyError:
            return web.HTTPBadRequest(text=f'Unknown block with id {id}!')

    @routes.get('/graph')
    async def get_graph(request):
        elkGraph = serialize_elk_graph(being)
        return json_response(elkGraph)

    @routes.get('/config')
    async def config(request):
        return json_response(CONFIG)

    return routes


def behavior_routes(behaviors) -> web.RouteTableDef:
    """API routes for being behaviors.

    Args:
        behaviors: All behaviors.

    Returns:
        Routes table for API app.
    """
    routes = web.RouteTableDef()
    behaviorLookup: Dict[int, Behavior] = {
        behavior.id: behavior
        for behavior in behaviors
    }

    @routes.get('/behaviors/{id}')
    async def load_behavior(request):
        id = int(request.match_info['id'])
        try:
            return json_response(behaviorLookup[id])
        except (ValueError, KeyError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)

    @routes.get('/behaviors/{id}/states')
    async def load_behavior_states(request):
        stateNames = list(BehaviorState.__members__)
        return json_response(stateNames)

    @routes.put('/behaviors/{id}/toggle_playback')
    async def toggle_behavior_playback(request):
        id = int(request.match_info['id'])
        try:
            behavior = behaviorLookup[id]
            if behavior.active:
                behavior.pause()
            else:
                behavior.play()
                behavior.update()  # Do one cycle so that we see which motion was last played

            return json_response(behavior)
        except (ValueError, KeyError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)

    @routes.put('/behaviors/{id}/params')
    async def receive_behavior_params(request):
        id = int(request.match_info['id'])
        try:
            params = await request.json()
            behavior = behaviorLookup[id]
            behavior.params = params
            return json_response(behavior)
        except json.JSONDecodeError:
            msg = f'Failed deserializing JSON behavior params!'
            return web.HTTPNotAcceptable(text=msg)
        except (ValueError, IndexError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)

    return routes


def motion_player_routes(motionPlayers, behaviors) -> web.RouteTableDef:
    """API routes for motion players. Also needs to know about behaviors. To
    pause them on some actions.

    Args:
        motionPlayers: All motion players.
        behaviors: All behaviors.

    Returns:
        Routes table for API app.
    """
    routes = web.RouteTableDef()
    mpLookup = { mp.id: mp for mp in motionPlayers }

    @routes.get('/motionPlayers')
    async def get_motion_players(request):
        """Inform front end of available motion players / motors."""
        return json_response(motionPlayers)

    @routes.post('/motionPlayers/play')
    async def play_curves(request):
        """Play multiple curves on multiple motion players in parallel."""
        for behavior in behaviors:
            behavior.pause()

        try:
            dct = await request.json(loads=loads)
            startTimes = []
            for idStr, curve in dct['armed'].items():
                id = int(idStr)  # JSON object keys become strings
                mp = mpLookup[id]
                t0 = mp.play_curve(curve, loop=dct['loop'], offset=dct['offset'])
                startTimes.append(t0)

            if not startTimes:
                return web.HTTPBadRequest(text='Invalid request!')

            return json_response({'startTime': min(startTimes)})
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Invalid request!')
        except ValueError as err:
            LOGGER.error(err)
            LOGGER.debug('dct: %s', dct)
            return web.HTTPBadRequest(text=f'Something went wrong with the spline. Raw data was: {dct}!')

    @routes.post('/motionPlayers/{id}/stop')
    async def stop_spline_playback(request):
        """Stop spline playback."""
        id = int(request.match_info['id'])
        try:
            mp = mpLookup[id]
            mp.stop()
            return respond_ok()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')

    @routes.post('/motionPlayers/stop')
    async def stop_all_spline_playbacks(request):
        """Stop all spline playbacks aka. Stop all motion players."""
        for mp in motionPlayers:
            mp.stop()

        return respond_ok()

    @routes.put('/motionPlayers/{id}/channels/{channel}/livePreview')
    async def live_preview(request):
        """Live preview of position value for motor."""
        id = int(request.match_info['id'])
        for behavior in behaviors:
            behavior.pause()

        channel = int(request.match_info['channel'])
        try:
            mp = mpLookup[id]
            if mp.playing:
                mp.stop()

            data = await request.json()
            position = data.get('position')
            if position is None or not math.isfinite(position):
                return web.HTTPBadRequest(text=f'Invalid value {position} for live preview!')

            mp.positionOutputs[channel].value = position
            return json_response()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} on channel {channel} does not exist!')
        except KeyError:
            return web.HTTPBadRequest(text='Could not parse spline!')

    return routes


def motor_routes(being)  -> web.RouteTableDef:
    """API routes for motors. Also needs to know about behaviors. To pause them
    on some actions.

    Args:
        being: Main being application instance.

    Returns:
        Routes table for API app.

    """
    routes = web.RouteTableDef()

    def pause_others():
        for behavior in being.behaviors:
            behavior.pause()

        for mp in being.motionPlayers:
            mp.stop()

    @routes.get('/motors')
    async def get_motors(request):
        return json_response(being.motors)

    @routes.put('/motors/disable')
    async def disable_motors(request):
        pause_others()
        being.disable_motors()
        return json_response(being.motors)

    @routes.put('/motors/enable')
    async def enable_motors(request):
        being.enable_motors()
        return json_response(being.motors)

    @routes.put('/motors/home')
    async def home_motors(request):
        pause_others()
        being.home_motors()
        return respond_ok()

    return routes


def misc_routes() -> web.RouteTableDef:
    """All other APIs which are not directly related to being, content,
    etc...
    """
    routes = web.RouteTableDef()

    @routes.post('/fit_curve')
    async def convert_trajectory(request):
        """Convert a trajectory array to a spline."""
        try:
            trajectory = await request.json()
            data = np.array(trajectory)
            t, *positionValues = data.T
            splines = [
                fit_spline(np.array([t, pos]).T, smoothing=1e-7)
                for pos in positionValues
            ]
            curve = Curve(splines)
            return json_response(curve)
        except ValueError:
            return web.HTTPBadRequest(text='Wrong trajectory data format. Has to be 2d!')

    return routes


def params_routes(params) -> web.RouteTableDef:
    """Dynamic routes for all Parameter blocks.

    Args:
        params: Parameter blocks.

    Returns:
        API routes.
    """
    # Same params ordering as in the config file(s).
    config = Config()
    for p in params:
        update_dict_recursively(config, p.configFile, default_factory=dict)
    for p in params:
        config.store(p.fullname, p)

    routes = web.RouteTableDef()

    @routes.get('/params')
    def get_params(request):
        """Get all parameter config entries."""
        LOGGER.debug('confg.data: %r', config.data)
        return json_response(config.data)

    async def get_param(request, param):
        """Get single param block."""
        LOGGER.debug('get_param() %s', param)
        return json_response(param)

    async def set_param(request, param):
        """Update value of parameter block."""
        value = await request.json()
        LOGGER.debug('set_param() %s %s', param, value)
        param.change(value)
        return json_response()

    for param in params:
        url = '/params/' + param.fullname

        # Important! functools.partial to capture param reference while looping
        routes.get(url)(functools.partial(get_param, param=param))
        routes.put(url)(functools.partial(set_param, param=param))

    return routes
