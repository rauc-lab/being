/**
 * Wrapper verbs around standard JS fetch.
 * @module js/fetching
 */


/**
 * HTTP GET request.
 * @param {string} url - URL parameter.
 * @returns {Promise} HTTP response.
 */
export function get(url) {
    return fetch(url, {method: "GET"});
}


/**
 * HTTP PUT request.
 * @param {string} url - URL parameter.
 * @returns {Promise} HTTP response.
 */
export function put(url) {
    return fetch(url, {method: "PUT"});
}


/**
 * HTTP POST request.
 * @param {string} url - URL parameter.
 * @returns {Promise} HTTP response.
 */
export function post(url) {
    return fetch(url, {method: "POST"});
}


/**
 * HTTP DELETE request. The odd one out since delete is a reserved JS
 * keyword...
 * @param {string} url - URL parameter.
 * @returns {Promise} HTTP response.
 */
export function delete_fetch(url) {
    return fetch(url, {method: "DELETE"});
}


/**
 * Fetch JSON data from or to url.
 * @param {string} url - URL parameter.
 * @param {string} method - HTTP method to use.
 * @param {Object} data - JSON data (for PUT and POST methods).
 */
export async function fetch_json(url, method = "GET", data = {}) {
    const options = {
        method: method,
        headers: { "Content-Type": "application/json" },
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
 * Get JSON data from url.
 * @param {string} url - URL parameter.
 * @returns {object} JSON payload.
 */
export function get_json(url) {
    return fetch_json(url, "GET");
}


/**
 * Post JSON data to url.
 * @param {string} url - URL parameter.
 * @param {object} data - Payload.
 */
export function post_json(url, data) {
    return fetch_json(url, "POST", data);
}


/**
 * Put JSON data to url.
 * @param {string} url - URL parameter.
 * @param {object} data - Payload.
 */
export function put_json(url, data) {
    return fetch_json(url, "PUT", data);
}
