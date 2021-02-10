"use strict";


/**
 * Two dimensional bounding box.
 */
class BBox {
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
     * Bound box center.
     * TODO: Needed? Kill it?
     */
    get center() {
        const [width, height] = this.size;
        return [
            this.ll[0] + .5 * width,
            this.ll[1] + .5 * height,
        ];
    }

    /**
     * Expand bounding box region.
     */
    expand(pt) {
        this.ll[0] = Math.min(this.ll[0], pt[0]);
        this.ll[1] = Math.min(this.ll[1], pt[1]);
        this.ur[0] = Math.max(this.ur[0], pt[0]);
        this.ur[1] = Math.max(this.ur[1], pt[1]);
    }
}
