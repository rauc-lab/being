"use strict";
import {array_shape} from "/static/js/math.js";
// TODO: Should we change serialization of splines? knots -> x, coefficients ->
// c? Same as like within Python / Scipy?


/**
 * Get unique elements in array.
 */
function unique_indices(arr) {
    let indices = [];
    let seen = [];
    arr.forEach((x, i) => {
        if (!seen.includes(x)) {
            seen.push(x);
            indices.push(i);
        }
    });

    return indices;
}


/**
 * Remove duplicate knots / coefficients from spline.
 */
function remove_duplicates(spline) {
    let cpy = {};
    Object.assign(cpy, spline);
    cpy.knots = [];
    cpy.coefficients = [];
    const idx = unique_indices(spline.knots);
    idx.forEach(i => {
        cpy.knots.push(spline.knots[i]);
        cpy.coefficients.push(spline.coefficients[i]);
    });
    return cpy;
}


/**
 * BPoly to Bézier control points.
 */
export function bpoly_to_bezier(spline) {
    spline = remove_duplicates(spline);
    let c = spline.coefficients;
    let x = spline.knots;
    let shape = array_shape(c);
    let ndim = shape.length;
    if (ndim !== 2) {
        throw "Only one dimensional splines supported at the moment!";
    }

    let order = shape[0];
    if (order < 2) {
        throw "Order not supported!";
    }

    let nSegments = shape[1];
    let cps = [];
    for (let seg=0; seg<nSegments; seg++) {
        let x0 = spline.knots[seg];
        let x1 = spline.knots[seg + 1];
        let dx = (x1 - x0) / (order - 1)
        let pts = [];
        for (let n=0; n<order; n++) {
            pts.push([x0 + n * dx, c[n][seg]])
        }
        cps.push(pts);
    }

    return cps;
}


export function bezier_to_bpoly(cps) {
    // TODO: Make me!
}
