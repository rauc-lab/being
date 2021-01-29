"use strict";
/**
 * Wait until DOM ready (from http://youmightnotneedjquery.com).
 */
function ready(fn) {
    if (document.readyState != 'loading'){
        fn();
    } else {
        document.addEventListener('DOMContentLoaded', fn);
    }
}


/**
 * Fetch JSON data from url.
 */
async function fetch_json(url) {
    const response = await fetch(url);
    return await response.json();
}


/**
 * Remove all children from HTML element (from http://youmightnotneedjquery.com).
 */
function remove_all_children(el) {
    while (el.firstChild) {
        el.removeChild(el.lastChild);
    }
}


export {ready, fetch_json, remove_all_children};
