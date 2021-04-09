/**
 * @module utils All kinds of util. Lots from http://youmightnotneedjquery.com.
 */


/**
 * Wait until DOM ready (from http://youmightnotneedjquery.com).
 * 
 * @param {function} fn - Callback.
 */
export function ready(fn) {
    if (document.readyState != "loading") {
        fn();
    } else {
        document.addEventListener("DOMContentLoaded", fn);
    }
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
        next: function () {
            //return sequence[idx++ % sequence.length];  // Actually no. idx unbounded.
            idx %= sequence.length;
            const pick = sequence[idx];
            idx += 1;
            return pick;
        }
    };
}


/**
 * Check if two arrays are equal (deep comparison).
 */
export function arrays_equal(a, b) {
    if (a instanceof Array && b instanceof Array) {
        if (a.length != b.length) {
            return false;
        }

        for (let i = 0; i < a.length; i++) {
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
export function assert(condition, message = "") {
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
        if (arr[mid] < val) {
            lower = mid + 1;
        } else {
            upper = mid;
        }
    }

    return lower;
}


/**
 * Add option to select.
 *
 * @param {HTMLElement} select Select element to append option to.
 * @param {String} name Option name.
 */
export function add_option(select, name) {
    const option = document.createElement("option");
    option.setAttribute("value", name);
    option.innerHTML = name;
    select.appendChild(option);
    return option;
}


/**
 * Test if the filename is valid on different operating systems
 */
export function is_valid_filename(fnm) {
    var rg1 = /^[^\\/:\*\?"<>\|]+$/; // forbidden characters \ / : * ? " < > |
    var rg2 = /^\./; // cannot start with dot (.)
    var rg3 = /^(nul|prn|con|lpt[0-9]|com[0-9])(\.|$)/i; // forbidden file names
    return rg1.test(fnm) && !rg2.test(fnm) && !rg3.test(fnm);
}


/**
 * Insert item in array at index.
 *
 * @param {Array} array 
 * @param {Number} index 
 * @param {object} item Object to insert.
 */
export function insert_in_array(array, index, item) {
    array.splice(index, 0, item);
}


/**
 * Remove item from array at index.
 *
 * @param {Array} array 
 * @param {Number} index Index to remove.
 */
export function remove_from_array(array, index) {
    array.splice(index, 1);
}
