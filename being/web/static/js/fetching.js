/**
 * @module fetching Wrapper verbs around standard fetch.
 */


export function get(url) {
    return fetch(url, {method: "GET"});
}


export function put(url) {
    return fetch(url, {method: "PUT"});
}


export function post(url) {
    return fetch(url, {method: "POST"});
}


// delete is a reseverd JS keyword
export function delete_fetch(url) {
    return fetch(url, {method: "DELETE"});
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


export function get_json(url) {
    return fetch_json(url, "GET");
}


export function post_json(url, data) {
    return fetch_json(url, "POST", data);
}


export function put_json(url, data) {
    return fetch_json(url, "PUT", data);
}