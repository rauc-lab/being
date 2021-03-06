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
 * Fetch JSON data from or to url.
 * 
 * @param {String} url URL address.
 * @param {String} method HTTP method.
 * @param {Object} data JSON data (for PUT and POST method)
 */
export async function fetch_json(url, method = "GET", data = {}) {
    const options = {
        method: method,
        headers: {"Content-Type": "application/json"},
    };
    if (method === "POST" || method === "PUT") {
        options["body"] = JSON.stringify(data);
    }

    const response = await fetch(url, options);
    if (!response.ok) {
        console.log("Response:", response);
        throw new Error("Something went wrong fetching data!");
    }

    return response.json();
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
            //return sequence[idx++ % sequence.length];  // Actually no. idx unbounded.
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
        if (a.length != b.length) {
            return false;
        }

        for (let i=0; i<a.length; i++) {
            if (!arrays_equal(a[i], b[i])) {
                return false;
            }
        }

        return true;
    } else {
        return a == b;
    }
}


/**
 * Assert something and throw an error if condition does not hold up.
 */
export function assert(condition, message="") {
    if (!condition) {
        throw ("AssertionError " + message).trim();
    }
}


/**
 * Find index to insert item into sorted array so that it stays sorted.
 */
export function searchsorted(arr, val) {
    let lower = 0;
    let upper = arr.length;
    while (lower < upper) {
        let mid = parseInt((lower + upper) / 2);
        if (arr[mid] < val)
            lower = mid + 1;
        else
            upper = mid;
    }

    return lower;
}