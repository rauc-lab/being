"use strict";
import { BPoly } from "/static/js/spline.js";
import { API } from "/static/js/config.js";
import { put, post, delete_fetch, get_json, post_json, put_json } from "/static/js/fetching.js";


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
    async live_preview(position, id) {
        return put_json(API + "/motors/" + id + "/livePreview", { "position": position });
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


    /**
    * Create a new spline on the backend. Content is a line with
    * arbitrary filename
    */
    async create_spline() {
        return post_json(API + "/motions");
    }


    /**
     * Save spline to backend.
     *
     * @param {BPoly} spline Spline instance to save.
     * @param {String} name Spline name in content.
     */
    async save_spline(spline, name) {
        const url = encodeURI(API + "/motions/" + name);
        return put_json(url, spline.to_dict());
    }


    /**
     * Duplicate motion in backend / content.
     *
     * @param {String} name Motion name.
     * @returns Fetch promise
     */
    async duplicate_spline(name) {
        let url = API + "/motions/" + name;
        url = encodeURI(url);
        return post(url);
    }


    /**
     * Rename spline in backend / content.
     *
     * @param {String} oldName Old spline name
     * @param {String} newName New spline name
     * @returns Fetch promise
     */
    async rename_spline(oldName, newName) {
        let url = API + "/motions/" + oldName + "?rename=" + newName;
        url = encodeURI(url);
        return put_json(url);
    }


    /**
     * Delete spline in backend / content.
     *
     * @param {String} name Spline name.
     * @returns Fetch promise.
     */
    async delete_spline(name) {
        let url = API + "/motions/" + name;
        url = encodeURI(url);
        return delete_fetch(url);
    }


    /**
     * Load entire content from backend / content.
     *
     * @returns Fetch promise
     */
    async fetch_splines() {
        return get_json("/api/motions");
    }
}
