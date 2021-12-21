/**
 * API definitions for communication with back-end.
 *
 * @module js/api
 */
import {objectify, anthropomorphify} from "/static/js/serialization.js";
import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";


/**
 * Being web API.
 */
export class Api {

    /**
     * Get all being blocks by id.
     *
     * @returns {Promise} Block id -> Being block object.
     */
    async get_blocks() {
        return get_json(API + "/blocks");
    }

    /**
     * Get output block ids for a given block id. All blocks that are connected
     * via value output connection.
     *
     * @param {number} id Block id.
     *
     * @returns {Promise} List of connected block ids. Empty list if no outgoing connections.
     */
    async get_index_of_value_outputs(id) {
        return get_json(API + "/blocks/" + id + "/index_of_value_outputs");
    }

    /**
     * Get graph of block network (ELK style object).
     * @returns {Promise} Graph object.
     */
    async get_graph() {
        return get_json(API + "/graph");
    }

    /**
     * Get being configurations.
     *
     * @returns {Promise} Being CONFIG dictionary.
     */
    async get_config() {
        return get_json(API + "/config");
    }

    /**
     * Fit curve from trajectory data.
     *
     * @param {array} trajectory Recorded trajectory. Row direction is time and
     *     column timestamp and position values [timestamp, x, y, ...].
     *
     * @returns {Promise} Fitted curve with smoothing splines.
     */
    async fit_curve(trajectory) {
        const dct = await post_json(API + "/fit_curve", trajectory);
        return objectify(dct);
    }


    /** Motor API */


    /**
     * Get motor infos.
     *
     * @returns {Promise} Array of motor objects.
     */
    async get_motor_infos() {
        return get_json(API + "/motors");
    }

    /**
     * Disable all motors in backend for motion recording.
     *
     * @returns {Promise} Array of updated motor infos.
     */
    async disable_motors() {
        return put_json(API + "/motors/disable");
    }

    /**
     * Enable all motors in backend after motion recording.
     *
     * @returns {Promise} Array of updated motor infos.
     */
    async enable_motors() {
        return put_json(API + "/motors/enable");
    }

    /**
     * Trigger homing in all motors.
     *
     * @returns {Promise} Standard HTTP response. 
     */
    async home_motors() {
        return put(API + "/motors/home");
    }

    /** Motion player API */

    /**
     * Get motion player infos.
     *
     * @returns {Promise} Array of motion player dictionaries.
     */
    async get_motion_player_infos() {
        return get_json(API + "/motionPlayers");
    }
    
    /**
     * Play multiple motion curves in backend.
     *
     * @param {object} armed Armed motion curves per motion player id.
     * @param {bool} loop If to loop motions.
     * @param {number} offset Start time offset in motion curves.
     *
     * @returns {number} Start timestamp of motion playback.
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
     *
     * @returns {Promise} Standard HTTP response.
     */
    async stop_spline_playback() {
        return post(API + "/motionPlayers/stop");
    }

    /**
     * Move motion player / motor to position.
     *
     * @param {number} position Position value in SI units.
     * @param {number} id Motion player id.
     * @param {number} channel Motion player output channel.
     *
     * @returns {Promise} Empty JSON object to signalize success.
     */
    async live_preview(position, id, channel = 0) {
        return put_json(API + "/motionPlayers/" + id + "/channels/" + channel + "/livePreview", {
            "position": position,
        });
    }

    /** Content API */

    /**
     * Get all motion curves. Returned a motion message with curves as [name, curve]
     * tuples (most recently modified order).
     *
     * @example
     * {
     *      type: "motions",
     *      curves: [
     *          ["some name", {"type": "Curve", ...}],
     *          ["other name", {"type": "Curve", ...}],
     *          // ...
     *      ]
     * }
     * 
     * @returns {object} Motions message object.
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

    /**
     * Get curve by name.
     *
     * @param {string} name Curve name.
     *
     * @returns {Curve} Curve instance.
     */
    async get_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        const dct = await get_json(url);
        return objectify(dct)
    }

    /**
     * Create a new curve.
     *
     * @param {string} name Curve name.
     * @param {Curve} curve Curve instance.
     *
     * @returns {Promise} Empty JSON object to signalize success.
     */
    async create_curve(name, curve) {
        const url = encodeURI(API + "/curves/" + name);
        return post_json(url, anthropomorphify(curve));
    }

    /**
     * Update a curve.
     *
     * @param {string} name Curve name.
     * @param {Curve} curve Curve instance.
     *
     * @returns {Promise} Empty JSON object to signalize success.
     */
    async update_curve(name, curve) {
        const url = encodeURI(API + "/curves/" + name);
        return post_json(url, anthropomorphify(curve));
    }

    /**
     * Delete a curve.
     *
     * @param {string} name Curve name.
     * @param {Curve} curve Curve instance.
     *
     * @returns {Promise} Empty JSON object to signalize success.
     */
    async delete_curve(name) {
        const url = encodeURI(API + "/curves/" + name);
        return delete_fetch(url);
    }

    /**
     * Rename a curve.
     *
     * @param {string} oldName Old curve name.
     * @param {string} newName New curve name.
     *
     * @returns {Promise} Empty JSON object to signalize success.
     */
    async rename_curve(oldName, newName) {
        const data = {
            oldName: oldName,
            newName: newName,
        };
        return put_json(API + "/rename_curve", data);
    }

    /**
     * Find a free name for a new curve.
     *
     * @param {string} [wishName=undefined] Wish name (if any). If undefined
     *     backend will use default new-curve-name "Untitled" and append
     *     ascending numbers to it if necessary.
     *
     * @returns {Promise} Next free curve name.
     */
    async find_free_name(wishName=undefined) {
        let uri = API + "/find-free-name";
        if (wishName !== undefined) {
            uri += "/" + wishName;
        }

        return get_json(encodeURI(uri));
    }

    /**
     * Download all curves as Zip.
     *
     * @returns {Promise} Zip file response
     */
    async download_all_curves_as_zip() {
        const url = encodeURI(API + "/download-zipped-curves");
        return fetch(url);
    }
}
