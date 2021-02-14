"use strict";


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
     */
    expand_by_bbox(bbox) {
        this.expand_by_point(bbox.ll);
        this.expand_by_point(bbox.ur);
    }
}


/**
 * Fit bounding box from array of 2D points.
 */
export function fit_bbox(pts) {
    let bbox = new BBox();
    bbox.expand_by_points(pts);
    return bbox;
}
