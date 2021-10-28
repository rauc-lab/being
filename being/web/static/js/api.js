/**
 *  @module api Back end API definitions.
 */
import {BPoly} from "/static/js/spline.js";
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
     * Fit spline from trajectory data.
     *
     * @param {Array} trajectory Recorded trajectory. Array of timestamps and position values.
     * @returns Fitted smoothing spline instance.
     */
    async fit_spline(trajectory) {
        const obj = await post_json(API + "/fit_spline", trajectory);
        return BPoly.from_object(obj);
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
     * Play spline in backend.
     */
    async play_spline(spline, id, loop = false, offset = 0) {
        const res = await post_json(API + "/motionPlayers/" + id + "/play", {
            "spline": spline.to_dict(),
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
     *          ["some name", {"type": "BPoly", ...}],
     *          ["other name", {"type": "BPoly", ...}],
     *          ...
     *      ]
     * }
     */
    async get_curves() {
        const url = encodeURI(API + "/curves");
        const msg = await get_json(url);
        msg.curves = msg.curves.map(entry => {
            const [name, dct] = entry;
            return [name, BPoly.from_object(dct)];
        });
        return msg;
    }

    async get_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        const obj = await get_json(url);
        return BPoly.from_object(obj);
    }

    async create_curve(name, spline) {
        const url = encodeURI(API + "/curves/" + name);
        return post_json(url, spline.to_dict());
    }

    async update_curve(name, spline) {
        const url = encodeURI(API + "/curves/" + name);
        return put_json(url, spline.to_dict());
    }

    async delete_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        return delete_fetch(url);
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
