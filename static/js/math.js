"use strict";

/**
 * Clip value to [lower, upper] boundaries.
 */
export function clip(value, lower=0, upper=1) {
    return Math.max(lower, Math.min(upper, value));
}


/**
 * Round number to given decimal places.
 */
export function round(number, ndigits=0) {
    const shift = Math.pow(10, ndigits)
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
 * Euclidean distance between two vectors.
 */
export function distance(a, b) {
    return Math.hypot(...subtract_arrays(b, a));
}


export function cartesian_to_polar(pt) {
    return [
        Math.hypot(pt[0], pt[1]),
        Math.atan2(pt[1], pt[0]),  // Yes, x and y are flipped!
    ]
}


export function polar_to_cartesian(pt) {
    return [
        pt[0] * Math.cos(pt[1]),
        pt[0] * Math.sin(pt[1]),
    ]
}


/* Numpy style array helpers */


/**
 * Shape of array.
 */
export function array_shape(arr) {
    let shape = [];
    while (arr instanceof Array) {
        shape.push(arr.length);
        arr = arr[0];
    }

    return shape;
}


/**
 * Number of dimensions of array.
 */
export function array_ndims(arr) {
    return array_shape(arr).length;
}


/**
 * Reshape array. Taken from math.js _reshape.
 */
export function array_reshape(array, shape) {
  let tmpArray = array
  let tmpArray2
  for (let sizeIndex = shape.length - 1; sizeIndex > 0; sizeIndex--) {
    const size = shape[sizeIndex]
    tmpArray2 = []
    const length = tmpArray.length / size
    for (let i = 0; i < length; i++) {
      tmpArray2.push(tmpArray.slice(i * size, (i + 1) * size))
    }
    tmpArray = tmpArray2
  }

  return tmpArray
}


/**
 * Array minimum value.
 * @param arr - Flat input array.
 * @returns Minimum value.
 */
export function array_min(arr) {
    return Math.min.apply(Math, arr);
}


/**
 * Array maximum value.
 * @param arr - Flat input array.
 * @returns Maximum value.
 */
export function array_max(arr) {
    return Math.max.apply(Math, arr);
}


/**
 * Create zeros array in arbitrary dimensions.
 */
export function zeros(dimensions) {
    let array = [];
    for (let i = 0; i < dimensions[0]; i++) {
        array.push(dimensions.length === 1 ? 0 : zeros(dimensions.slice(1)));
    }

    return array;
}


/**
 * Ascending integer array for given length. 
 */
export function arange(length) {
    return [...Array(length).keys()];
}


/**
 * Linspace array of given length.
 */
export function linspace(start=0., stop=1., num=50) {
    console.assert(num > 1, "num > 1!");
    const step = (stop - start) / (num - 1);
    return arange(num).map((i) => i * step);
}


/**
 * Element wise add two arrays together.
 */
export function add_arrays(augend, addend) {
    return augend.map((aug, i) => aug + addend[i]);
}


/**
 * Element wise multiply two arrays together.
 */
export function multiply_scalar(factor, array) {
    return array.map(e => factor * e);
}


/**
 * Element wise divide two arrays.
 */
export function divide_arrays(dividend, divisor) {
    return dividend.map((div, i) => div / divisor[i]);
}


/**
 * Element wise subtract two array from each other.
 */
export function subtract_arrays(minuend, subtrahend) {
    return minuend.map((min, i) => min - subtrahend[i]);
}


/**
 * Transpose array (untested.)
 */
export function transpose_array(arr) {
    return arr[0].map((_, colIndex) => arr.map(row => row[colIndex]));
}
