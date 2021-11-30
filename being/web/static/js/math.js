/**
 * @module math All kinds of math helpers.
 */
import { TAU } from "/static/js/constants.js";


/**
 * Clip value to [lower, upper] boundaries. Note: No lower < upper validation!
 */
export function clip(value, lower=0, upper=1) {
    return Math.max(lower, Math.min(upper, value));
}


/**
 * Round number to given decimal places.
 */
export function round(number, ndigits=0) {
    const shift = Math.pow(10, ndigits);
    return Math.round(number * shift) / shift;
}


/**
 * Normal Gaussian random distribution.
 *
 * Resources:
 *     https://en.wikipedia.org/wiki/Box–Muller_transform
 */
export function normal(mean=0, std=1.) {
    const u0 = Math.random();
    const u1 = Math.random();
    const z0 = Math.sqrt(-2.0 * Math.log(u0)) * Math.cos(TAU * u1);
    //const z1 = Math.sqrt(-2.0 * Math.log(u0)) * Math.sin(TAU * u1);
    return z0 * std + mean;
}


/**
 * Positive numbers only modulo operation.
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
 */
export function floor_division(number, divisor) {
    return Math.floor(number / divisor);
}

/**
 * Check if two values are reasonably close to each other. Adapted from pythons
 * math.isclose() function.
 */
export function isclose(a, b, rel_tol=1e-9, abs_tol=0) {
    if (a === b)
        return true

    const diff = Math.abs(b - a);
    return (((diff <= Math.abs(rel_tol * b)) || (diff <= Math.abs(rel_tol * a))) || (diff <= abs_tol));
}
