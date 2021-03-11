"use strict";
/**
 * Spline stuff. Some constants and BPoly wrapper.
 */
import {array_shape, array_min, array_max} from "/static/js/math.js";
import {deep_copy, last_element} from "/static/js/utils.js";
import {BBox} from "/static/js/bbox.js";
import {assert} from "/static/js/utils.js";
import {clip} from "/static/js/math.js";


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


const LEFT = "left";
const RIGHT = "right";


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
     * Segment width.
     */
    _dx(seg) {
        return this.x[seg+1] - this.x[seg];
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
     * Get first derative value at knot position.
     *
     * @param {Number} nr Knot number.
     * @param {String} side Which side of the knot.
     */
    get_derivative_at_knot(nr, side=RIGHT) {
        if (side === RIGHT) {
            assert(0 <= nr && nr < this.n_segments);
            const seg = nr;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.;
            }
            return this.degree * (this.c[FIRST_CP][seg] - this.c[KNOT][seg]) / dx;
        } else if (side === LEFT) {
            assert(0 < nr && nr <= this.n_segments);
            const seg = nr - 1;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.;
            }

            const knot = KNOT + this.degree;
            return this.degree * (this.c[knot][seg] - this.c[knot-1][seg]) / dx;
        }
    }

    /**
     * Adjust control points for a given dervative value.
     *
     * @param {Number} nr Knot number.
     * @param {Number} value Derivative value to ensure.
     * @param {String} side Which side of the knot.
     */
    set_derivative_at_knot(nr, value, side=RIGHT) {
        if (side === RIGHT) {
            assert(0 <= nr && nr < this.n_segments);
            const seg = nr;
            this.c[FIRST_CP][seg] = this._dx(seg) * value / this.degree + this.c[KNOT][seg];
        } else {
            assert(0 < nr && nr <= this.n_segments);
            const seg = nr - 1;
            const knot = KNOT + this.degree;
            this.c[knot-1][seg] = this.c[knot][seg] - this._dx(seg) * value / this.degree;
        }
    }


    /**
     * Move knot to another position.
     *
     * @param {Number} nr Knot number.
     * @param {Array} pos New knot position.
     * @param {Bool} c1 C1 continuity (move surounding control points as well)
     */
    position_knot(nr, pos, c1 = false) {
        let left = -Infinity;
        let right = Infinity;
        let leftDer = 0;
        let rightDer = 0;
        if (nr > 0) {
            left = this.x[nr - 1];
            leftDer = this.get_derivative_at_knot(nr, LEFT);
        }

        if (nr < this.n_segments) {
            right = this.x[nr + 1];
            rightDer = this.get_derivative_at_knot(nr, RIGHT);
        }

        this.x[nr] = clip(pos[0], left, right);

        if (nr > 0) {
            const knot = KNOT + this.degree;
            const prevSeg = nr - 1;
            this.c[knot][prevSeg] = pos[1];
            if (c1) {
                this.set_derivative_at_knot(nr, leftDer, LEFT);
            }
        }

        if (nr < this.n_segments) {
            const seg = nr;
            this.c[KNOT][seg] = pos[1];
            if (c1) {
                this.set_derivative_at_knot(nr, rightDer, RIGHT);
            }
        }
    }


    /**
     * Move control point around (only vertically).
     *
     * @param {Number} seg Segment number.
     * @param {Number} nr Knot / control point number.
     * @param {Number} y New y position of control point.
     * @param {Bool} c1 Ensure C1 continnuity.
     */
    position_control_point(seg, nr, y, c1 = false) {
        const leftMost = (nr === FIRST_CP) && (seg === 0);
        const rightMost = (nr === SECOND_CP) && (seg === this.n_segments - 1);
        if (!c1 || leftMost || rightMost) {
            this.c[nr][seg] = y;
            return;
        }

        if (nr === FIRST_CP) {
            const der = this.get_derivative_at_knot(seg, RIGHT);
            this.c[FIRST_CP][seg] = y;
            this.set_derivative_at_knot(seg, der, LEFT);
        } else if (nr === SECOND_CP) {
            const der = this.get_derivative_at_knot(seg+1, LEFT);
            this.c[SECOND_CP][seg] = y;
            this.set_derivative_at_knot(seg+1, der, RIGHT);
        }
    }


    /**
     * Bézier control point.
     *
     * @param seg Segment index.
     * @param nr Control point index. E.g. for cubic 0 -> left knot, 1 -> First control point, etc...
     */
    point(seg, nr=0) {
        if (seg === this.x.length - 1) {
            const knot = KNOT + this.degree;
            return [this.end, last_element(this.c[knot])];
        }

        return [this._x(seg, nr), this.c[nr][seg]];
    }

    /**
     * Create a copy for the spline (deep copy).
     */
    copy() {
        return new BPoly(deep_copy(this.c), deep_copy(this.x), this.extrapolate, this.axis);
    }

    /**
     * Convert BPoly instance to dict representation.
     */
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
