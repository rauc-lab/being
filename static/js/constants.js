"use strict";
/**
 * All kind of constants.
 */


 /**
  * Milliseconds constants.
  * 
  * @constant
  * @type {int}
  */
export const MS = 1000;


/**
 * Two PI 
 * 
 * @constant
 * @type {float}
 */
export const TAU = 2.0 * Math.PI;


/**
 * Spline orders.
 */
export const Order = Object.freeze({
    "CUBIC": 4,
    "QUADRATIC": 3,
    "LINEAR": 2,
});


/**
 * Spline degree.
 */
export const Degree = Object.freeze({
    "CUBIC": 3,
    "QUADRATIC": 2,
    "LINEAR": 1,
});
