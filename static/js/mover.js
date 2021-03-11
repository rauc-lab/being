"use strict";
import { clip } from "/static/js/math.js";
import { KNOT, FIRST_CP, SECOND_CP, Degree } from "/static/js/spline.js";
import { assert } from "/static/js/utils.js";


/** Minimum knot distance episolon */
export const EPS = 1e-3;


/**
 * Spline mover.
 *
 * Manages spline dragging and editing. Keeps a backup copy of the original
 * spline as `orig` so that we can do delta manipulations.
 */
export class Mover {
    constructor(spline) {
        assert(spline.degree == Degree.CUBIC, "Only cubic splines supported for now!");
        this.orig = spline;
        this.spline = spline.copy();
    }

    /**
     * Move knot around for some delta.
     *
     * @param nr - Knot number to move.
     * @param delta - Delta 2d offset vector. Data space.
     * @param c1 - C1 continuity.
     */
    move_knot(nr, delta, c1 = true) {
        const xmin = (nr > 0) ? this.orig.x[nr - 1] + EPS : 0; // Allow only for kausal splines
        const xmax = (nr < this.orig.n_segments) ? this.orig.x[nr + 1] - EPS : Infinity;

        // Move knot horizontally
        this.spline.x[nr] = clip(this.orig.x[nr] + delta[0], xmin, xmax);
        if (nr > 0) {
            // Move knot vertically on the left
            const degree = this.spline.degree;
            this.spline.c[degree][nr - 1] = this.orig.c[degree][nr - 1] + delta[1];
        }

        if (nr < this.spline.n_segments) {
            // Move knot vertically on the right
            this.spline.c[KNOT][nr] = this.orig.c[KNOT][nr] + delta[1];
        }

        // Move control points
        if (nr == this.spline.n_segments) {
            this.move_control_point(nr - 1, SECOND_CP, delta, false);
        } else if (c1) {
            this.move_control_point(nr, FIRST_CP, delta);
        } else {
            this.move_control_point(nr, FIRST_CP, delta, false);
            this.move_control_point(nr - 1, SECOND_CP, delta, false);
        }
    }

    /**
     * X axis spacing ratio between two consecutive segments
     */
    _ratio(seg) {
        return this.spline._dx(seg + 1) / this.spline._dx(seg);
    }

    /**
     * Move control point around by some delta.
     */
    move_control_point(seg, nr, delta, c1 = true) {
        // Move control point vertically
        this.spline.c[nr][seg] = this.orig.c[nr][seg] + delta[1];

        // TODO: This is messy. Any better way?
        const leftMost = (seg === 0) && (nr === FIRST_CP);
        const rightMost = (seg === this.spline.n_segments - 1) && (nr === SECOND_CP);
        if (leftMost || rightMost) {
            return;
        }

        // Move adjacent control point vertically
        if (c1 && this.spline.degree == Degree.CUBIC) {
            if (nr == FIRST_CP) {
                const y = this.spline.c[KNOT][seg];
                const q = this._ratio(seg - 1);
                const dy = this.spline.c[FIRST_CP][seg] - y;
                this.spline.c[SECOND_CP][seg - 1] = y - dy / q;
            } else if (nr == SECOND_CP) {
                const y = this.spline.c[KNOT][seg + 1];
                const q = this._ratio(seg);
                const dy = this.spline.c[SECOND_CP][seg] - y;
                this.spline.c[FIRST_CP][seg + 1] = y - q * dy;
            }
        }
    }
}
