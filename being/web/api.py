"""API calls / controller for communication between front end and being components."""
import collections
import itertools
import json
import math
from typing import Dict

from aiohttp import web

from being.behavior import State as BehaviorState, Behavior
from being.being import Being
from being.config import CONFIG
from being.connectables import ValueOutput, _ValueContainer
from being.content import Content
from being.logging import get_logger
from being.motors import Motor, HomingState
from being.serialization import loads, spline_from_dict, register_enum
from being.spline import fit_spline
from being.utils import filter_by_type
from being.web.responses import respond_ok, json_response


LOGGER = get_logger(__name__)
"""API module logger."""


register_enum(HomingState)


def messageify(obj) -> collections.OrderedDict:
    """Serialize being objects and wrap them inside a message object.

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

    if isinstance(obj, Motor):
        return collections.OrderedDict([
            ('type', 'motor-update'),
            ('motor', obj),
        ])

    if isinstance(obj, list) and all(isinstance(o, Motor) for o in obj):
        return collections.OrderedDict([
            ('type', 'motor-updates'),
            ('motors', obj),
        ])

    raise ValueError(f'Do not know how to messagiy {obj}!')


def content_controller(content: Content) -> web.RouteTableDef:
    """Controller for content model. Build Rest API routes. Wrap content
    instance in API.

    Args:
        content: Content model.

    Returns:
        Routes table for API app.
    """
    routes = web.RouteTableDef()

    @routes.get('/motions')
    async def get_all_motions(request):
        return json_response(content.dict_motions())

    @routes.get('/motions2')
    async def get_all_motions_2(request):
        return json_response(content.dict_motions_2())

    @routes.get('/find-free-name')
    async def find_free_name(request):
        return json_response(content.find_free_name())

    @routes.get('/find-free-name/{wishName}')
    async def find_free_name_wish_name(request):
        wishName = request.match_info['wishName']
        return json_response(content.find_free_name(wishName=wishName))

    @routes.get('/motions/{name}')
    async def get_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        spline = content.load_motion(name)
        return json_response(spline)

    @routes.post('/motions/{name}')
    async def create_motion_by_name(request):
        name = request.match_info['name']
        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON spline!')

        content.save_motion(name, spline)
        return json_response()

    @routes.put('/motions/{name}')
    async def update_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        try:
            spline = await request.json(loads=loads)
        except json.JSONDecodeError:
            return web.HTTPNotAcceptable(text='Failed deserializing JSON spline!')

        content.save_motion(name, spline)
        return json_response()

    @routes.delete('/motions/{name}')
    async def delete_motion_by_name(request):
        name = request.match_info['name']
        if not content.motion_exists(name):
            return web.HTTPNotFound(text=f'Motion {name!r} does not exist!')

        content.delete_motion(name)
        return json_response()

    return routes


def serialize_elk_graph(blocks):
    """Serialize blocks to ELK style graph dict serialization."""
    # Why yet another graph serialization? Because of edge connection type and
    # double edges. For execOrder double edges do not matter, but they do for
    # the block diagram
    # ELK style graph object
    elkGraph = collections.OrderedDict([
        ('id', 'root'),
        ('children', []),
        ('edges', []),
    ])
    queue = collections.deque(blocks)
    visited = set()
    edgeIdCounter = itertools.count()
    while queue:
        block = queue.popleft()
        if block in visited:
            continue

        visited.add(block)
        elkGraph['children'].append({
            'id': block.id,
            'name': type(block).__name__,
        })

        for output in block.outputs:
            connectionType = 'value' if isinstance(output, _ValueContainer) else 'message'
            for input_ in output.outgoingConnections:
                if input_.owner and input_.owner is not block:
                    elkGraph['edges'].append({
                        'id': 'edge %d' % next(edgeIdCounter),
                        'connectionType': connectionType,
                        'sources': [block.id],
                        'targets': [input_.owner.id],
                    })

    return elkGraph


def being_controller(being: Being) -> web.RouteTableDef:
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
        elkGraph = serialize_elk_graph(being.execOrder)
        return json_response(elkGraph)

    @routes.get('/config')
    async def config(request):
        return json_response(CONFIG)

    return routes


def behavior_controllers(behaviors) -> web.RouteTableDef:
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

    @routes.get('/behaviors/{id}/states')
    async def load_behavior_states(request):
        stateNames = list(BehaviorState.__members__)
        return json_response(stateNames)


    @routes.get('/behaviors/{id}')
    async def load_behavior(request):
        id = int(request.match_info['id'])
        try:
            return json_response(behaviorLookup[id])
        except (ValueError, KeyError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)


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


def motion_player_controllers(motionPlayers, behaviors) -> web.RouteTableDef:
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

    @routes.post('/motionPlayers/{id}/play')
    async def start_spline_playback(request):
        """Start spline playback for a received spline from front end."""
        id = int(request.match_info['id'])
        for behavior in behaviors:
            behavior.pause()

        try:
            mp = mpLookup[id]
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


def motor_controllers(motors, behaviors, motionPlayers)  -> web.RouteTableDef:
    """API routes for motors. Also needs to know about behaviors. To pause them
    on some actions.

    Args:
        motionPlayers: All motion players.
        behaviors: All behaviors.

    Returns:
        Routes table for API app.

    """
    routes = web.RouteTableDef()

    def pause_others():
        for behavior in behaviors:
            behavior.pause()

        for mp in motionPlayers:
            mp.stop()

    @routes.get('/motors')
    async def get_motors(request):
        return json_response(motors)

    @routes.put('/motors/disable')
    async def disable_motors(request):
        pause_others()
        for motor in motors:
            motor.disable(publish=False)

        return json_response(motors)

    @routes.put('/motors/enable')
    async def enable_motors(request):
        for motor in motors:
            motor.enable(publish=False)

        return json_response(motors)

    @routes.put('/motors/home')
    async def home_motors(request):
        pause_others()
        for motor in motors:
            motor.home()

        return respond_ok()

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
            spline = fit_spline(trajectory, smoothing=1e-9)
            return json_response(spline)
        except ValueError:
            return web.HTTPBadRequest(text='Wrong trajectory data format. Has to be 2d!')

    return routes
