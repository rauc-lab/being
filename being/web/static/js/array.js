/**
 * @module array Numpy style array helpers.
 */

import {assert, arrays_equal} from "/static/js/utils.js";


/**
 * Shape of an array.
 *
 * @param {Array} array to determine shape from.
 * @returns {Array} Shape of array.
 */
export function array_shape(array) {
    let shape = [];
    while (array instanceof Array) {
        shape.push(array.length);
        array = array[0];
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
    let tmpArray = array;
    let tmpArray2;
    for (let sizeIndex = shape.length - 1; sizeIndex > 0; sizeIndex--) {
        const size = shape[sizeIndex];
        tmpArray2 = [];
        const length = tmpArray.length / size;
        for (let i = 0; i < length; i++) {
            tmpArray2.push(tmpArray.slice(i * size, (i + 1) * size));
        }
        tmpArray = tmpArray2;
    }

    return tmpArray;
}


/**
 * Array minimum value.
 * @param {Array} arr Flat input array.
 * @returns Minimum value.
 */
export function array_min(arr) {
    return Math.min.apply(Math, arr);
}


/**
 * Array maximum value.
 * @param {Array} arr Flat input array.
 * @returns Maximum value.
 */
export function array_max(arr) {
    return Math.max.apply(Math, arr);
}


/**
 * Create zeros array for a given shape.
 *
 * @param {Array} shape Input shape
 * @returns {Array} Zero array of given shape
 */
export function zeros(shape) {
    let array = [];
    for (let i = 0; i < shape[0]; i++) {
        array.push(shape.length === 1 ? 0 : zeros(shape.slice(1)));
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


export function array_full(shape, fillValue) {
    const n = shape.reduce((acc, val) => {
        return acc * val;
    });
    const raw = Array(n).fill(fillValue);
    return array_reshape(raw, shape);
}


assert(arrays_equal( array_full([3], 1), [1, 1, 1]));
assert(arrays_equal( array_full([1, 3], 1), [[1, 1, 1]]));
