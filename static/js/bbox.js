/**
 * Bounding box
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
        return subtract_arrays(this.ur, this.ll);
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
        return multiply_scalar(.5, add_arrays(this.ll, this.ur));
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