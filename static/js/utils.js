"use strict";
/**
 * All kinds of util. Lots from http://youmightnotneedjquery.com.
 */


/**
 * Wait until DOM ready (from http://youmightnotneedjquery.com).
 * 
 * @param {function} fn - Callback.
 */
export function ready(fn) {
    if (document.readyState != "loading"){
        fn();
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
}


/**
 * Fetch JSON data from url.
 * 
 * @param {string} url - URL to get JSON data from.
 */
export async function fetch_json(url) {
    const response = await fetch(url);
    return await response.json();
}


/**
 * Remove all children from HTML element (from http://youmightnotneedjquery.com).
 * 
 * @param {HTMLElement} el - HTML element to remove all children from.
 */
export function remove_all_children(el) {
    while (el.firstChild) {
        el.removeChild(el.lastChild);
    }
}


/**
 * Clear array in place.
 */
export function clear_array(arr) {
    arr.length = 0;
}


/**
 * Get last element of array.
 */
export function last_element(arr) {
    return arr[arr.length - 1];
}


/**
 * Deep copy JS array / object.
 */
export function deep_copy(obj) {
    return JSON.parse(JSON.stringify(obj));
}


/**
 * Cycle through sequence iterator.
 */
export function cycle(sequence) {
    // TODO: Use proper JS generators / iterator / what ever it is called
    let idx = 0;
    return {
        next: function() {
            //return sequence[idx++ % sequence.length];
            idx %= sequence.length;
            const pick = sequence[idx];
            idx += 1;
            return pick;
        }
    }
}


/**
 * Check if two arrays are equal (deep comparison).
 */
export function arrays_equal(a, b) {
    if (a instanceof Array && b instanceof Array) {
        if (a.length != b.length)
            return false;

        for (let i=0; i<a.length; i++)
            if (!arrays_equal(a[i], b[i]))
                return false;

        return true;
    } else {
        return a == b;
    }
}


/**
 * Assert something and throw an error if condition does not hold up.
 */
export function assert(condition, message="") {
    if (!condition)
        throw ("AssertionError " + message).trim();
}
