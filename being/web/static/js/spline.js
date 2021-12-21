/**
 * Spline stuff. Some constants and BPoly wrapper. Spline data container. No
 * spline evaluation. Sampling splines for plotting is handled by SVG. Helpers
 * for manipulating the shape of the spline:
 *   - Moving control points around
 *   - Changing the derivative at a given knot
 *   - Inserting / removing knots
 *
 * @module js/spline
 */
import {
    array_shape, array_min, array_max, array_ndims, arange, zeros, array_full,
    array_reshape, multiply_scalar, diff_array,
} from "/static/js/array.js";
import {deep_copy, last_element} from "/static/js/utils.js";
import {BBox} from "/static/js/bbox.js";
import {assert, searchsorted, insert_in_array, remove_from_array} from "/static/js/utils.js";
import {clip, floor_division} from "/static/js/math.js";


/** @const {number} - First knot index for BPoly coefficent matrix. */
export const KNOT = 0;

/** @const {number} - First control point index for BPoly coefficent matrix. */
export const FIRST_CP = 1;

/** @const {number} - Second control point index for BPoly coefficent matrix. */
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

/** @const {number} - Depth of coefficients tensor. */
export const COEFFICIENTS_DEPTH = 3;


/**
 * Determine spline polynom order.
 * @param {BPoly} spline - Input spline.
 * @returns {number} Spline order.
 */
export function spline_order(spline) {
    const shape = array_shape(spline.coefficients);
    return shape[0];
}


/**
 * Determine spline polynom degree.
 * @param {BPoly} spline - Input spline.
 * @returns {number} Spline degree.
 */
export function spline_degree(spline) {
    return spline_order(spline) - 1;
}


/**
 * Create all zero spline for a given number of dimensions.
 * @param {number} [ndim=1] - Number of spline dimensions
 * @returns {BPoly} Zero spline.
 */
export function zero_spline(ndim=1) {
    return new BPoly(zeros([4, 1, ndim]), [0., 1.]);
}


/**
 * Duplicate entry in array at index.
 * @param {array} arr - Input array.
 * @param {number} index - Target index.
 */
function duplicate_entry_in_array(arr, index) {
    index = clip(index, 0, arr.length - 1);
    const cpy = deep_copy(arr[index]);
    insert_in_array(arr, index, cpy);
}


/**
 * Duplicate column in matrix.
 * @param {array} mtrx - Input matrix (at least 2D array).
 * @param {number} col - Column number.
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
 * @param {array} c - Spline coefficients.
 * @param {array} x - Spline knots.
 * @param {boolean} extrapolate - Extrapolation flag (not really used here but
 *     for completeness).
 * @param {number} axis - Spline axis (for completeness but not in use).
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
     * @returns {BPoly} New spline instance.
     */
    static from_dict(dct) {
        return new BPoly(dct.coefficients, dct.knots, dct.extrapolate, dct.axis);
    }

    /**
     * Start time of spline.
     * @type {number}
     */
    get start() {
        return this.x[0];
    }

    /**
     * End time of spline.
     * @type {number}
     */
    get end() {
        return last_element(this.x);
    }

    /**
     * Duration of the spline.
     * @type {number}
     */
    get duration() {
        return this.end - this.start;
    }

    /**
     * Number of segments in the spline.
     * @type {number}
     */
    get n_segments() {
        return this.x.length - 1;
    }

    /**
     * Minimum value of the spline. Not the global maximum!
     * @type {number}
     */
    get min() {
        return array_min(this.c.flat(COEFFICIENTS_DEPTH));
    }

    /**
     * Maximum value of the spline. Not the global minimum!
     * @type {number}
     */
    get max() {
        return array_max(this.c.flat(COEFFICIENTS_DEPTH));
    }

    /**
     * Calculate bounding box of spline (approximately).
     * @returns {BBox} Spline bounding box.
     */
    bbox() {
        return new BBox([this.start, this.min], [this.end, this.max]);
    }

    /**
     * Spline segment width.
     * @param {number} seg - Spline segment number.
     * @returns {number} Segment width.
     */
    _dx(seg) {
        return this.x[seg+1] - this.x[seg];
    }

    /**
     * Time value of a given Bézier control point. Along first axis. The
     * intermediate points are distributed equally between two knots.
     * @param {number} seg - Segment number.
     * @param {number} nr - Control point number. E.g. for a cubic spline 0 ->
     *     left knot, 1 -> first control point, 2 -> second control point and 3
     *     -> right control point.
     * @returns {number} Control point time or x value.
     */
    _x(seg, nr=0) {
        const alpha = nr / this.degree;
        return (1 - alpha) * this.x[seg] + alpha * this.x[seg+1];
    }

    /**
     * Get first derivative of spline at a knot.
     * @param {number} nr - Knot number.
     * @param {string} [side=right] - Which side of the knot. Right side by default.
     * @param {number} [dim=0] - Target spline dimension.
     * @returns {number} Derivative value.
     */
    get_derivative_at_knot(nr, side=RIGHT, dim=0) {
        if (side === RIGHT) {
            assert(0 <= nr && nr < this.n_segments);
            const seg = nr;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.0;
            }

            return this.degree * (this.c[FIRST_CP][seg][dim] - this.c[KNOT][seg][dim]) / dx;
        } else if (side === LEFT) {
            assert(0 < nr && nr <= this.n_segments);
            const seg = nr - 1;
            const dx = this._dx(seg);
            if (dx === 0) {
                return 0.0;
            }

            const knot = KNOT + this.degree;
            return this.degree * (this.c[knot][seg][dim] - this.c[knot-1][seg][dim]) / dx;
        }
    }

    /**
     * Set derivative value at a knot. This will affect adjacent coefficient values.
     * @param {number} nr - Knot number.
     * @param {number} value - Desired derivative value at knot.
     * @param {string} [side=right] - Which side of the knot. Right side by default.
     * @param {number} [dim=0] - Target spline dimension.
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
     * Move knot around.
     * @param {number} nr - Knot number.
     * @param {array} pos - Target position.
     * @param {boolean} [c1=false] - C1 continuity. If true move surrounding
     *     control points as well.
     * @param {number} [dim=0] - Target spline dimension.
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
     * @param {number} seg - Segment number.
     * @param {number} nr - Knot / control point number.
     * @param {number} y - Target vertical y position.
     * @param {boolean} [c1=false] - Ensure C1 continuity.
     * @param {number} [dim=0] - Target spline dimension.
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
     * Get Bézier control point for SVG paths.
     * @param {number} seg - Segment number.
     * @param {number} nr - Knot / control point number.
     * @param {number} [dim=0] - Spline dimension.
     * @returns {array} 2D [x, y] point.
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
     * @param {array} pos - [x, y] position.
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
     * @param {number} knotNr - Knot number.
     * @returns {boolean} If we are dealing with the last knot of the spline.
     */
    _is_last_knot(knotNr) {
        return (knotNr === this.n_segments);
    }

    /**
     * Remove knot from spline.
     * @param {number} knotNr - Knot number to remove.
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
     * Create a deep copy of the spline.
     */
    copy() {
        // TODO: deep_copy(this.x) -> [...this.x]?
        return new BPoly(deep_copy(this.c), deep_copy(this.x), this.extrapolate, this.axis);
    }

    /**
     * Convert BPoly instance to dict representation.
     * @returns {object} Dictionary representation for serialization.
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
     * @param {Bbox} bbox - Limiting bounding box.
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

    /**
     * Scale position values by some scalar factor (in place).
     * @param {number} factor - Scale factor.
     */
    scale(factor) {
        const shape = array_shape(this.c);
        this.c = array_reshape(multiply_scalar(factor, this.c.flat(COEFFICIENTS_DEPTH)), shape);
    }

    /**
     * Stretch in time by some factor (in place).
     * @param {number} factor - Stretch factor.
     */
    stretch(factor) {
        this.x = multiply_scalar(factor, this.x);
    }

    /**
     * Shift in time by some offset (in place).
     * @param {number} offset - Shift offset.
     */
    shift(offset) {
        offset = Math.max(offset, -this.start);
        this.x = this.x.map(pos => {
            return pos + offset;
        });
    }

    /**
     * Flip horizontally (in place). Mirrored along time axis.
     */
    flip_horizontally() {
        // Flip knots
        const delta = diff_array(this.x);
        delta.reverse();
        const newX = [this.x[0]];
        delta.forEach(dx => {
            newX.push(last_element(newX) + dx);
        });
        this.x = newX;

        // Flip coeffs
        this.c.forEach(row => { row.reverse(); });
        this.c.reverse();
    }

    /**
     * Flip vertically (in place). Retrograde.
     */
    flip_vertically() {
        const shape = array_shape(this.c)
        const cvals = this.c.flat(COEFFICIENTS_DEPTH);
        if (cvals.length === 0) {
            return;
        }

        const maxc = array_max(cvals);
        const newcvals = cvals.map(val => maxc - val);
        this.c = array_reshape(newcvals, shape)
    };
}
