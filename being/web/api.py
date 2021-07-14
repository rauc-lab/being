"""API calls / controller for communication between front end and being components."""
import collections
import json
import math
from typing import ForwardRef, Dict

from aiohttp import web

from being.behavior import State as BehaviorState, Behavior
from being.content import Content
from being.logging import get_logger
from being.motors import MOTOR_CHANGED, Motor
from being.serialization import loads, spline_from_dict
from being.spline import fit_spline
from being.web.responses import respond_ok, json_response


#from being.motors import MOTOR_CHANGED, HomingState
#from being.serialization import register_enum
#register_enum(HomingState)


LOGGER = get_logger(__name__)
"""API module logger."""

Being = ForwardRef('Being')


# TODO: Why not replacing serializer functions with proper serialization? Block.to_dict()...


def connected_motors(motionPlayer):
    for output in motionPlayer.positionOutputs:
        for input_ in output.outgoingConnections:
            if isinstance(input_.owner, Motor):
                yield input_.owner


def serialize_behavior(behavior):
    return {
        'type': 'behavior-update',
        'id': behavior.id,
        'active': behavior.active,
        'state': behavior.state,
        'lastPlayed': behavior.lastPlayed,
        'params': behavior._params,
    }


def serialize_motion_players(being):
    """Return list of motion player / motors informations."""
    for nr, mp in enumerate(being.motionPlayers):
        actualOutputs = []
        motors = []
        lengths = []
        for motor in connected_motors(mp):
            motors.append(motor)
            actualOutputs.append(motor.output)
            lengths.append(motor.length)

        yield {
            'id': nr,
            'actualValueIndices': [being.valueOutputs.index(out) for out in actualOutputs],
            'lengths': lengths,
            'ndim': mp.ndim,
        }


def serialize_motor(motor):
    return collections.OrderedDict([
        ('type', 'motor-update'),
        ('id', motor.id),
        ('motorType', type(motor).__name__),
        #('length', motor.length),
        ('enabled', motor.enabled()),
        #('homed', motor.homed),
    ])


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


def being_controller(being: Being) -> web.RouteTableDef:
    """API routes for being object.

    Args:
        being: Being instance to wrap up in API.
    """
    routes = web.RouteTableDef()

    @routes.get('/motors')
    async def get_motors(request):
        return json_response([serialize_motor(motor) for motor in being.motors])

    @routes.put('/motors/disable')
    async def disable_motors(request):
        being.pause_behaviors()
        for motor in being.motors:
            motor.disable()

        return respond_ok()

    @routes.put('/motors/enable')
    async def enable_motors(request):
        for motor in being.motors:
            motor.enable()

        return respond_ok()

    @routes.get('/motionPlayers')
    async def get_motion_players(request):
        """Inform front end of available motion players / motors."""
        infos = list(serialize_motion_players(being))
        return json_response(infos)

    @routes.post('/motionPlayers/{id}/play')
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

    @routes.post('/motionPlayers/{id}/stop')
    async def stop_spline_playback(request):
        """Stop spline playback."""
        id = int(request.match_info['id'])
        try:
            mp = being.motionPlayers[id]
            mp.stop()
            return respond_ok()
        except IndexError:
            return web.HTTPBadRequest(text=f'Motion player with id {id} does not exist!')

    @routes.post('/motionPlayers/stop')
    async def stop_all_spline_playbacks(request):
        """Stop all spline playbacks aka. Stop all motion players."""
        for mp in being.motionPlayers:
            mp.stop()

        return respond_ok()

    @routes.put('/motionPlayers/{id}/channels/{channel}/livePreview')
    async def live_preview(request):
        """Live preview of position value for motor."""
        being.pause_behaviors()
        id = int(request.match_info['id'])
        channel = int(request.match_info['channel'])
        try:
            mp = being.motionPlayers[id]
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


def behavior_controllers(behaviors) -> web.RouteTableDef:
    """API routes for being behavior."""
    routes = web.RouteTableDef()
    behaviorLookup: Dict[int, Behavior] = {
        behavior.id: behavior
        for behavior in behaviors
    }
    """Behavior id -> Behavior instance lookup."""

    @routes.get('/behaviors/{id}/states')
    async def load_behavior_states(request):
        stateNames = list(BehaviorState.__members__)
        return json_response(stateNames)


    @routes.get('/behaviors/{id}')
    async def load_behavior_infos(request):
        try:
            id = int(request.match_info['id'])
            return json_response(serialize_behavior(behaviorLookup[id]))
        except (ValueError, KeyError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)


    @routes.put('/behaviors/{id}/toggle_playback')
    async def toggle_behavior_playback(request):
        try:
            id = int(request.match_info['id'])
            behavior = behaviorLookup[id]
            if behavior.active:
                behavior.pause()
            else:
                behavior.play()

            return json_response(serialize_behavior(behavior))
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
            return json_response(behavior.params)
        except json.JSONDecodeError:
            msg = f'Failed deserializing JSON behavior params!'
            return web.HTTPNotAcceptable(text=msg)
        except (ValueError, IndexError):
            msg = f'Behavior with id {id} does not exist!'
            return web.HTTPBadRequest(text=msg)

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
