/**
 * @module bbox Bounding box class.
 */
import { clip } from "/static/js/math.js";
import { deep_copy } from "/static/js/utils.js";


/**
 * Two dimensional bounding box.
 */
export class BBox {
    constructor(ll=[Infinity, Infinity], ur=[-Infinity, -Infinity]) {
        this.ll = ll;
        this.ur = ur;
    }

    /**
     * Bounding box size.
     */
    get size() {
        return [
            this.ur[0] - this.ll[0],
            this.ur[1] - this.ll[1],
        ];
    }

    /**
     * Bounding box width.
     */
    get width() {
        return this.ur[0] - this.ll[0];
    }

    /**
     * Bounding box height.
     */
    get height() {
        return this.ur[1] - this.ll[1];
    }

    /**
     * Get leftmost x value.
     */
    get left() {
        return this.ll[0];
    }

    /**
     * Set leftmost x value.
     */
    set left(pos) {
        this.ll[0] = pos;
    }

    /**
     * Get rightmost x value.
     */
    get right() {
        return this.ur[0];
    }

    /**
     * Set rightmost x value.
     */
    set right(value) {
        this.ur[0] = value;
    }

    /**
     * Reset to infinite bounding box.
     */
    reset() {
        this.ll = [Infinity, Infinity];
        this.ur = [-Infinity, -Infinity];
    }

    /**
     * Expand bounding box region.
     */
    expand_by_point(pt) {
        this.ll[0] = Math.min(this.ll[0], pt[0]);
        this.ll[1] = Math.min(this.ll[1], pt[1]);
        this.ur[0] = Math.max(this.ur[0], pt[0]);
        this.ur[1] = Math.max(this.ur[1], pt[1]);
    }

    /**
     * Expand bounding box region for some point.
     */
    expand_by_points(pts) {
        pts.forEach(pt => this.expand_by_point(pt));
    }

    /**
     * Expand bounding box region for another bounding box.
     *
     * @param {BBox} bbox - Bounding box to expand this bounding box with.
     */
    expand_by_bbox(bbox) {
        this.expand_by_point(bbox.ll);
        this.expand_by_point(bbox.ur);
    }

    /**
     * Clip point inside bounding box.
     *
     * @param {Array} pt - 2D point to clip.
     */
    clip_point(pt) {
        return [
            clip(pt[0], this.ll[0], this.ur[0]),
            clip(pt[1], this.ll[1], this.ur[1]),
        ];
    }

    /**
     * Copy bounding box.
     */
    copy() {
        return new BBox(deep_copy(this.ll), deep_copy(this.ur));
    }
}