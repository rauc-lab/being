/**
 * All kinds of math helpers.
 * @module js/math
 */
import { TAU } from "/static/js/constants.js";


/**
 * Clip value to [lower, upper] boundaries. Note: No lower < upper validation!
 * @param {number} value - Number to clip.
 * @param {number} [lower=0] - Lower bound.
 * @param {number} [upper=1] - Upper bound.
 * @returns {number} Clipped number.
 */
export function clip(value, lower=0, upper=1) {
    return Math.max(lower, Math.min(upper, value));
}


/**
 * Round number to given decimal places.
 * @param {number} number - Input number to round.
 * @param {number} [ndigits=0] - Digit number.
 * @returns {number} Rounded number.
 */
export function round(number, ndigits=0) {
    const shift = Math.pow(10, ndigits);
    return Math.round(number * shift) / shift;
}


/**
 * Normal Gaussian random distribution. See
 * `Box-Muller Transform <https://en.wikipedia.org/wiki/Box–Muller_transform>`_.
 * @param {number} [mean=0] - Mean value of distribution.
 * @param {number} [std=1] - Standard deviation of distribution.
 * @returns {number} Random number.
 */
export function normal(mean=0, std=1.) {
    const u0 = Math.random();
    const u1 = Math.random();
    const z0 = Math.sqrt(-2.0 * Math.log(u0)) * Math.cos(TAU * u1);
    //const z1 = Math.sqrt(-2.0 * Math.log(u0)) * Math.sin(TAU * u1);
    return z0 * std + mean;
}


/**
 * Positive numbers only modulo operation. Euclidean modulo operation (?).
 * @param {number} dividend.
 * @param {number} divisor.
 * @returns {number} Remainder.
 */
export function mod(dividend, divisor) {
    let remainder = dividend % divisor;
    if (remainder < 0) {
        remainder += divisor;
    }

    return remainder;
}


/**
 * Perform floor division between two number.
 * @param {number} number - Number to divide.
 * @param {number} divisor.
 * @returns {number} Quotient.
 */
export function floor_division(number, divisor) {
    return Math.floor(number / divisor);
}


/**
 * Check if two values are reasonably close to each other. Adapted from pythons
 * math.isclose() function.
 * @param {number} a - First number.
 * @param {number} b - Second number.
 * @param {number} [rel_tol=1e-9] - Relative tolerance.
 * @param {number} [abs_tol=0] - Absolute tolerance.
 * @returns {boolean} If the two numbers are close.
 */
export function isclose(a, b, rel_tol=1e-9, abs_tol=0) {
    if (a === b) {
        return true;
    }

    const diff = Math.abs(b - a);
    return (((diff <= Math.abs(rel_tol * b)) || (diff <= Math.abs(rel_tol * a))) || (diff <= abs_tol));
}
