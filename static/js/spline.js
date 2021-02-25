"use strict";
import {array_shape} from "/static/js/math.js";


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
