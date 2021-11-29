/**
 *  @module api Back end API definitions.
 */
import {objectify, anthropomorphify} from "/static/js/serialization.js";
import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";


export class Api {


    /** General being and misc API */


    async get_blocks() {
        return get_json(API + "/blocks");
    }

    async get_index_of_value_outputs(id) {
        return get_json(API + "/blocks/" + id + "/index_of_value_outputs");
    }

    /**
     * Get graph of block network.
     *
     * @returns Graph object.
     */
    async get_graph() {
        return get_json(API + "/graph");
    }

    async get_config() {
        return get_json(API + "/config");
    }

    /**
     * Fit curve from trajectory data.
     *
     * @param {Array} trajectory Recorded trajectory. Array of timestamps and position values.
     * @returns Fitted curve with smoothing splines.
     */
    async fit_curve(trajectory) {
        const dct = await post_json(API + "/fit_curve", trajectory);
        return objectify(dct);
    }


    /** Motor API */


    /**
     * Get current motor infos.
     */
    async get_motor_infos() {
        return get_json(API + "/motors");
    }

    /**
     * Disable all motors in backend for motion recording.
     */
    async disable_motors() {
        return put_json(API + "/motors/disable");
    }

    /**
     * Enable all motors in backend after motion recording.
     */
    async enable_motors() {
        return put_json(API + "/motors/enable");
    }

    /**
     * Trigger homing in all motors.
     */
    async home_motors() {
        return put(API + "/motors/home");
    }

    /**
     * Get available motor infos from backend. 
     *
     * @returns Array of motor info dictionaries.
     */
    async get_motion_player_infos() {
        return get_json(API + "/motionPlayers");
    }


    /** Motion player API */

    /**
     * Play multiple curves in back-end.
     */
    async play_multiple_curves(armed, loop = false, offset = 0) {
        const armSer = {};
        for (const [mpId, curve] of Object.entries(armed)) {
            armSer[mpId] = curve.to_dict();
        }
        const res = await post_json(API + "/motionPlayers/play", {
            "armed": armSer,
            "loop": loop,
            "offset": offset,
        });
        return res["startTime"];
    }

    /**
     * Stop all spline playback in backend.
     */
    async stop_spline_playback() {
        return post(API + "/motionPlayers/stop");
    }

    /**
     * Move motor in backend to position.
     *
     * @param {Number} position Vertical y position of linear motor.
     */
    async live_preview(position, id, channel = 0) {
        return put_json(API + "/motionPlayers/" + id + "/channels/" + channel + "/livePreview", {
            "position": position,
        });
    }

    /** Content API */

    /**
     * Get all curves. Returned a motion message with curves as [name, curve]
     * tuples (most recently modified order).
     *
     * {
     *      type: "motions",
     *      curves: [
     *          ["some name", {"type": "Curve", ...}],
     *          ["other name", {"type": "Curve", ...}],
     *          ...
     *      ]
     * }
     */
    async get_curves() {
        const url = encodeURI(API + "/curves");
        const msg = await get_json(url);
        msg.curves = msg.curves.map(entry => {
            const [name, dct] = entry;
            return [name, objectify(dct)];
        });
        return msg;
    }

    async get_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        const dct = await get_json(url);
        return objectify(dct)
    }

    async create_curve(name, curve) {
        const url = encodeURI(API + "/curves/" + name);
        return post_json(url, anthropomorphify(curve));
    }

    async update_curve(name, curve) {
        const url = encodeURI(API + "/curves/" + name);
        return post_json(url, anthropomorphify(curve));
    }

    async delete_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        return delete_fetch(url);
    }

    async rename_curve(oldName, newName) {
        const data = {
            oldName: oldName,
            newName: newName,
        };
        return put_json(API + "/rename_curve", data);
    }

    async find_free_name(wishName=undefined) {
        let uri = API + "/find-free-name";
        if (wishName !== undefined) {
            uri += "/" + wishName;
        }

        return get_json(encodeURI(uri));
    }

    async download_all_curves_as_zip() {
        const url = encodeURI(API + "/download-zipped-curves");
        return fetch(url);
    }


    /** Behavior API */


    async load_behavior_states() {
        return get_json(API + "/behavior/states");
    }

    async load_behavior_infos() {
        return get_json(API + "/behavior");
    }

    async send_behavior_params(params) {
        return put_json(API + "/behavior/params", params);
    }

    async toggle_behavior_playback() {
        return put_json(API + "/behavior/toggle_playback");
    }
}
