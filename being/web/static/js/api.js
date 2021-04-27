/**
 *  @module api Back end API definitions.
 */
import {BPoly} from "/static/js/spline.js";
import {API} from "/static/js/config.js";
import {put, post, delete_fetch, get_json, post_json, put_json} from "/static/js/fetching.js";


export class Api {
    /**
     * Get available motor infos from backend. 
     *
     * @returns Array of motor info dictionaries.
     */
    async get_motor_infos() {
        return get_json(API + "/motors");
    }

    /**
     * Play spline in backend.
     */
    async play_spline(spline, id, loop = false, offset = 0) {
        const res = await post_json(API + "/motors/" + id + "/play", {
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
        return post(API + "/motors/stop");
    }

    /**
     * Move motor in backend to position.
     *
     * @param {Number} position Vertical y position of linear motor.
     */
    async live_preview(position, id, channel = 0) {
        return put_json(API + "/motors/" + id + "/channels/" + channel + "/livePreview", {
            "position": position,
        });
    }

    /**
     * Disable all motors in backend for motion recording.
     */
    async disable_motors() {
        return put(API + "/motors/disenable");
    }

    /**
     * Enable all motors in backend after motion recording.
     */
    async enable_motors() {
        return put(API + "/motors/enable");
    }

    /**
     * Fit spline from trajectory data.
     *
     * @param {Array} trajectory Recorded trajectory. Array of timestamps and positoin values.
     * @returns Fitted smoothing spline instance.
     */
    async fit_spline(trajectory) {
        const obj = await post_json(API + "/fit_spline", trajectory);
        return BPoly.from_object(obj);
    }

    async find_free_name(wishName=null) {
        let uri = API + "/find-free-name";
        if (wishName !== null) {
            uri += "/" + wishName;
        }

        return get_json(encodeURI(uri));
    }

    async get_spline(name) {
        const url = encodeURI(API + "/motions/" + name);
        const obj = await get_json(url);
        return BPoly.from_object(obj);
    }

    async create_spline(name, spline) {
        const url = encodeURI(API + "/motions/" + name);
        return post_json(url, spline.to_dict());
    }

    async update_spline(name, spline) {
        const url = encodeURI(API + "/motions/" + name);
        return post_json(url, spline.to_dict());
    }

    async delete_spline(name) {
        const url = encodeURI(API + "/motions/" + name);
        return delete_fetch(url);
    }

    /**
     * Load entire content from backend / content.
     *
     * @returns Fetch promise
     */
    async fetch_splines() {
        return get_json(API + "/motions");
    }

    async load_motions() {
        return get_json(API + "/motions2");
    }

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
