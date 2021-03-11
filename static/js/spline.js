"use strict";
/**
 * Spline stuff. Some constants and BPoly wrapper.
 */
import {array_shape, array_min, array_max} from "/static/js/math.js";
import {deep_copy, last_element} from "/static/js/utils.js";
import {BBox} from "/static/js/bbox.js";


/** Named indices for BPoly coefficents matrix */
export const KNOT = 0;
export const FIRST_CP = 1;
export const SECOND_CP = 2;


/** Spline orders */
export const Order = Object.freeze({
    "CUBIC": 4,
    "QUADRATIC": 3,
    "LINEAR": 2,
    "CONSTANT": 1,
});


/** Spline degree */
export const Degree = Object.freeze({
    "CUBIC": 3,
    "QUADRATIC": 2,
    "LINEAR": 1,
    "CONSTANT": 0,
});


/**
 * Get order of spline.
 */
export function spline_order(spline) {
    const shape = array_shape(spline.coefficients);
    return shape[0];
}


/**
 * Get degree of spline.
 */
export function spline_degree(spline) {
    return spline_order(spline) - 1;
}


/**
 * Assure c0 continuity in spline coefficient matrix.
 *
 * @param {Spline} spline
 */
export function smooth_out_spline(spline) {
    const degree = spline.degree;
    for (let seg = 0; seg < spline.n_segments; seg++) {
        if (seg > 0) {
            spline.c[KNOT + degree][seg - 1] = spline.c[KNOT][seg];
        }
    }
}

/**
 * JS BPoly wrapper.
 *
 * BPoly is used by scipys interpolate package in Python. We do not need to
 * sample the spline but rather the extract the Bézier control points. And we
 * need a data structure for storing and manipulating the spline.
 */
export class BPoly {
    constructor(c, x, extrapolate=false, axis=0) {
        this.c = c;
        this.x = x;
        this.extrapolate = extrapolate;
        this.axis = axis;

        this.order = c.length;
        this.degree = c.length - 1;
    }


    /**
     * Construct from BPoly object.
     */
    static from_object(dct) {
        return new BPoly(dct.coefficients, dct.knots, dct.extrapolate, dct.axis)
    }


    /**
     * Start time of spline.
     */
    get start() {
        return this.x[0];
    }


    /**
     * End time of spline.
     */
    get end() {
        return last_element(this.x);
    }

    /**
     * Duration of the spline.
     */
    get duration() {
        return this.end - this.start;
    }


    /**
     * Number of segments in the spline.
     */
    get n_segments() {
        return this.x.length - 1;
    }


    /**
     * Minimum value of the spline. Not the global maximum!
     */
    get min() {
        return array_min(this.c.flat());
    }


    /**
     * Maximum value of the spline. Not the global minimum!
     */
    get max() {
        return array_max(this.c.flat());
    }


    /**
     * Calculate bounding box of spline (approximately).
     */
    bbox() {
        return new BBox([this.start, this.min], [this.end, this.max]);
    }


    /**
     * Inter segment interval. Segment width divided depending on spline degree.
     */
    _dx(seg) {
        if (this.degree == Degree.CONSTANT) {
            return (this.x[seg+1] - this.x[seg]);
        }

        return (this.x[seg+1] - this.x[seg]) / this.degree;
    }


    /**
     * X position of a given Bézier control point.
     *
     * @param seg - Segment index.
     * @param nr - Control point index. E.g. for cubic 0 -> left knot, 1 ->
     * first control point, 2 -> second control point, 3 -> right knot.
     */
    _x(seg, nr=0) {
        const alpha = nr / this.degree;
        return (1 - alpha) * this.x[seg] + alpha * this.x[seg+1];
    }


    /**
     * Bézier control point.
     *
     * @param seg - Segment index.
     * @param nr - Control point index. E.g. for cubic 0 -> left knot, 1 ->
     */
    point(seg, nr=0) {
        if (seg == this.x.length - 1) {
            return [this.end, last_element(this.c[this.degree])];
        }

        return [this._x(seg, nr), this.c[nr][seg]];
    }

    /**
     * Create a copy for the spline (deep copy).
     */
    copy() {
        return new BPoly(deep_copy(this.c), deep_copy(this.x), this.extrapolate, this.axis);
    }

    to_dict() {
        return {
            "type": "BPoly",
            "extrapolate": this.extrapolate,
            "axis": 0,
            "knots": this.x,
            "coefficients": this.c,
        }
    }
}
