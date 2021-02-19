"use strict";
/**
 * All kind of constants.
 */


/** Milliseconds constants */
export const MS = 1000;

/** One PI */
export const PI = Math.PI;

/** Two PI */
export const TAU = 2.0 * PI;

/** Spline orders */
export const Order = Object.freeze({
    "CUBIC": 4,
    "QUADRATIC": 3,
    "LINEAR": 2,
});

/** Spline degree */
export const Degree = Object.freeze({
    "CUBIC": 3,
    "QUADRATIC": 2,
    "LINEAR": 1,
});
