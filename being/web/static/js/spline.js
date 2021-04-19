/**
 * @module spline Spline stuff. Some constants and BPoly wrapper. Spline data container.
 */
import {array_shape, array_min, array_max, array_ndims, arange, zeros, array_full} from "/static/js/array.js";
import {deep_copy, last_element} from "/static/js/utils.js";
import {BBox} from "/static/js/bbox.js";
import {assert, searchsorted, insert_in_array, remove_from_array} from "/static/js/utils.js";
import {clip, floor_division} from "/static/js/math.js";


/** @const {number} - Named indices for BPoly coefficents matrix */
export const KNOT = 0;
export const FIRST_CP = 1;
export const SECOND_CP = 2;

/** @const {object} - Spline order enum. */
export const Order = Object.freeze({
    "CUBIC": 4,
    "QUADRATIC": 3,
    "LINEAR": 2,
    "CONSTANT": 1,
});

/** @const {object} - Spline degree enum.*/
export const Degree = Object.freeze({
    "CUBIC": 3,
    "QUADRATIC": 2,
    "LINEAR": 1,
    "CONSTANT": 0,
});

/** @const {string} - Left side of knot string literal. */
export const LEFT = "left";

/** @const {string} - Right side of knot string literal. */
export const RIGHT = "right";

/** @const {Number} - Depth of coefficients tensor. */
export const COEFFICIENTS_DEPTH = 3;

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
 * Create zero spline for a given number of dimensions.
 *
 * @param {Number} ndim Number of spline dimensions
 * @returns {BPoly} Zero spline.
 */
export function zero_spline(ndim=1) {
    return new BPoly(zeros([4, 1, ndim]), [0., 1.]);
}


/**
 * Duplicate entry in array at index.
 * @param {Array} array 
 * @param {Number} index 
 */
function duplicate_entry_in_array(array, index) {
    index = clip(index, 0, array.length - 1);
    const cpy = deep_copy(array[index]);
    insert_in_array(array, index, cpy);
}


/**
 * Duplicate column in matrix.
 * @param {Array} mtrx At least 2d array.
 * @param {Number} col Column number.
 */
function duplicate_column_in_matrix(mtrx, col) {
    mtrx.forEach(row => {
        duplicate_entry_in_array(row, col);
    });
}


/**
 * Validate coefficients matrix / tensor. Transform scalar coefficients to 1D
 * coefficients.
 */
function _vectorize_coefficients(c) {
    const ndims = array_ndims(c);
    if (ndims === 3) {
        return c;
    }

    if (ndims === 2) {
        return c.map(row => {
            return row.map(value => {
                return [value];
            });
        });
    }

    throw `Coefficients have to be ndims 2 or 3. Not ${ndims}!`;
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
        c = _vectorize_coefficients(c);
        const shape = array_shape(c);
        assert(shape.length === 3, "Coefficients c have the wrong shape " + shape);
        assert(shape[1] === x.length - 1, "Mismatching coefficients and knots!");
        this.c = c;
        this.x = x;
        this.extrapolate = extrapolate;
        this.axis = axis;
        this.order = shape[0];
        this.degree = this.order - 1;
        this.ndim = shape[2];
    }

    /**
     * Construct from BPoly object.
     */
    static from_object(dct) {
        return new BPoly(dct.coefficients, dct.knots, dct.extrapolate, dct.axis);
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
        return array_min(this.c.flat(COEFFICIENTS_DEPTH));
    }

    /**
     * Maximum value of the spline. Not the global minimum!
     */
    get max() {
        return array_max(this.c.flat(COEFFICIENTS_DEPTH));
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
    get_derivative_at_knot(nr, side=RIGHT, dim=0) {
        if (side === RIGHT) {
            assert(0 <= nr && nr < this.n_segments);
            const seg = nr;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.;
            }

            return this.degree * (this.c[FIRST_CP][seg][dim] - this.c[KNOT][seg][dim]) / dx;
        } else if (side === LEFT) {
            assert(0 < nr && nr <= this.n_segments);
            const seg = nr - 1;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.;
            }

            const knot = KNOT + this.degree;
            return this.degree * (this.c[knot][seg][dim] - this.c[knot-1][seg][dim]) / dx;
        }
    }

    /**
     * Adjust control points for a given derivative value.
     *
     * @param {Number} nr Knot number.
     * @param {Number} value Derivative value to ensure.
     * @param {String} side Which side of the knot.
     */
    set_derivative_at_knot(nr, value, side=RIGHT, dim=0) {
        if (side === RIGHT) {
            assert(0 <= nr && nr < this.n_segments);
            const seg = nr;
            this.c[FIRST_CP][seg][dim] = this._dx(seg) * value / this.degree + this.c[KNOT][seg][dim];
        } else {
            assert(0 < nr && nr <= this.n_segments);
            const seg = nr - 1;
            const knot = KNOT + this.degree;
            this.c[knot-1][seg][dim] = this.c[knot][seg][dim] - this._dx(seg) * value / this.degree;
        }
    }

    /**
     * Move knot to another position.
     *
     * @param {Number} nr Knot number.
     * @param {Array} pos New knot position.
     * @param {Bool} c1 C1 continuity (move surrounding control points as well)
     */
    position_knot(nr, pos, c1 = false, dim = 0) {
        let left = -Infinity;
        let right = Infinity;
        let leftDer = zeros([this.ndim]);
        let rightDer = zeros([this.ndim]);
        const dims = arange(this.ndim);
        if (nr > 0) {
            left = this.x[nr - 1];
            leftDer = dims.map(dim => {
                return this.get_derivative_at_knot(nr, LEFT, dim);
            });
        }

        if (nr < this.n_segments) {
            right = this.x[nr + 1];
            rightDer = dims.map(dim => {
                return this.get_derivative_at_knot(nr, RIGHT, dim);
            });
        }

        this.x[nr] = clip(pos[0], left, right);

        if (nr > 0) {
            const knot = KNOT + this.degree;
            const prevSeg = nr - 1;
            this.c[knot][prevSeg][dim] = pos[1];
            if (c1) {
                leftDer.forEach((der, dim) => {
                    this.set_derivative_at_knot(nr, der, LEFT, dim);
                });
            }
        }

        if (nr < this.n_segments) {
            const seg = nr;
            this.c[KNOT][seg][dim] = pos[1];
            if (c1) {
                rightDer.forEach((der, dim) => {
                    this.set_derivative_at_knot(nr, der, RIGHT, dim);
                });
            }
        }
    }

    /**
     * Move control point around (only vertically).
     *
     * @param {Number} seg Segment number.
     * @param {Number} nr Knot / control point number.
     * @param {Number} y New y position of control point.
     * @param {Bool} c1 Ensure C1 continuity.
     */
    position_control_point(seg, nr, y, c1 = false, dim = 0) {
        const leftMost = (nr === FIRST_CP) && (seg === 0);
        const rightMost = (nr === SECOND_CP) && (seg === this.n_segments - 1);
        if (!c1 || leftMost || rightMost) {
            this.c[nr][seg][dim] = y;
            return;
        }

        if (nr === FIRST_CP) {
            const der = this.get_derivative_at_knot(seg, RIGHT, dim);
            this.c[FIRST_CP][seg][dim] = y;
            this.set_derivative_at_knot(seg, der, LEFT, dim);
        } else if (nr === SECOND_CP) {
            const der = this.get_derivative_at_knot(seg+1, LEFT, dim);
            this.c[SECOND_CP][seg][dim] = y;
            this.set_derivative_at_knot(seg+1, der, RIGHT, dim);
        }
    }

    /**
     * Bézier control point.
     *
     * @param {Number} seg Segment index.
     * @param {Number} nr Control point index. E.g. for cubic 0 -> left knot, 1
     *     -> First control point, etc...
     */
    point(seg, nr=0, dim=0) {
        if (seg === this.n_segments) {
            const knot = KNOT + this.degree;
            return [this.end, last_element(this.c[knot])[dim]];
        }

        return [this._x(seg, nr), this.c[nr][seg][dim]];
    }

    /**
     * Insert new knot into the spline.
     *
     * @param {Array} pos Knot x, y position.
     */
    insert_knot(pos) {
        const x = this.x;
        const c = this.c;
        const index = searchsorted(x, pos[0]);
        const nextKnot = KNOT + this.degree;
        const seg = index - 1;
        const length = x.length;
        insert_in_array(x, index, pos[0]);
        duplicate_column_in_matrix(c, index);
        const vals = array_full([this.ndim], pos[1]);
        if (seg === -1) {
            // Before first segment
            c[KNOT][0] = vals;
            c[FIRST_CP][0] = vals;
            c[SECOND_CP][0] = deep_copy(c[KNOT][1]);
            c[nextKnot][0] = deep_copy(c[KNOT][1]);
        } else if (seg === length - 1) {
            // After last segment
            c[KNOT][seg] = deep_copy(c[nextKnot][seg-1]);
            c[FIRST_CP][seg] = deep_copy(c[nextKnot][seg-1]);
            c[SECOND_CP][seg] = vals;
            c[nextKnot][seg] = vals;
        } else {
            // Somewhere between two segments
            c[SECOND_CP][seg] = vals;
            c[nextKnot][seg] = vals;
            c[KNOT][seg+1] = vals;
            c[FIRST_CP][seg+1] = vals;
            if (seg + 2 < c[KNOT].length) {
                c[SECOND_CP][seg+1] = deep_copy(c[KNOT][seg+2]);
                c[nextKnot][seg+1] = deep_copy(c[KNOT][seg+2]);
            }
        }
    }

    /**
     * Check if we are dealing with the last spline knot.
     *
     * @param {Number} knotNr Knot number.
     * @returns If we are dealing with the last knot of the spline.
     */
    _is_last_knot(knotNr) {
        return (knotNr === this.n_segments);
    }

    /**
     * Remove knot from spline.
     *
     * @param {Number} knotNr Knot number to remove.
     */
    remove_knot(knotNr) {
        if (this._is_last_knot(knotNr)) {
            this.x.pop();
            this.c.forEach(row => {
                row.pop();
            });
            return;
        }

        // Prepare continuity / copy parts of the coefficients from seg ->
        // seg-1 before deleting col seg.
        const seg = knotNr;
        const half = floor_division(this.order, 2);
        for (let i=half; i<this.order; i++) {
            this.c[i][seg-1] = deep_copy(this.c[i][seg]);
        }

        remove_from_array(this.x, knotNr);
        this.c.forEach(row => {
            remove_from_array(row, seg);
        });
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
        };
    }

    /**
     * Restrict all knots and control points to a bounding box.
     *
     * @param {Bbox} bbox Limits bounding box.
     */
    restrict_to_bbox(bbox) {
        const [xmin, ymin] = bbox.ll;
        const [xmax, ymax] = bbox.ur;
        this.x.forEach((knot, i) => {
            this.x[i] = clip(knot, xmin, xmax);
        });

        this.c.forEach((coeffs, row) => {
            coeffs.forEach((coeff, col) => {
                coeff.forEach((val, nr) => {
                    this.c[row][col][nr] = clip(val, ymin, ymax);
                });
            });
        });
    }
}
