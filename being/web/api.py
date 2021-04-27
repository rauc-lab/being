"""API calls / controller for communication between front end and being components."""
import json
import math
from typing import ForwardRef

from aiohttp import web

from being.behavior import State
from being.content import Content
from being.logging import get_logger
from being.motor import _MotorBase
from being.serialization import loads, spline_from_dict
from being.spline import fit_spline
from being.web.responses import respond_ok, json_response


LOGGER = get_logger(__name__)
"""API module logger."""

Being = ForwardRef('Being')


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


def connected_motors(motionPlayer):
    for output in motionPlayer.positionOutputs:
        for input_ in output.outgoingConnections:
            if isinstance(input_.owner, _MotorBase):
                yield input_.owner


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

    @routes.put('/motors/{id}/channels/{channel}/livePreview')
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

    @routes.put('/motors/disenable')
    async def disenable_drives(request):
        being.pause_behaviors()
        if being.network:
            being.network.engage_drives()

        return respond_ok()

    @routes.put('/motors/enable')
    async def enable_drives(request):
        if being.network:
            being.network.enable_drives()

        return respond_ok()

    return routes


def behavior_controller(behavior) -> web.RouteTableDef:
    """API routes for being behavior."""
    # TODO: For now we only support 1x behavior instance. Needs to be expanded for the future
    routes = web.RouteTableDef()

    @routes.get('/behavior/states')
    async def get_states(request):
        stateNames = list(State.__members__)
        return json_response(stateNames)

    @routes.get('/behavior')
    async def get_info(request):
        return json_response(behavior.infos())

    @routes.put('/behavior/toggle_playback')
    async def toggle_playback(request):
        if behavior.active:
            behavior.pause()
        else:
            behavior.play()

        return json_response(behavior.infos())

    @routes.get('/behavior/params')
    async def get_params(request):
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
            spline = fit_spline(trajectory, smoothing=1e-9)
            return json_response(spline)
        except ValueError:
            return web.HTTPBadRequest(text='Wrong trajectory data format. Has to be 2d!')

    return routes
