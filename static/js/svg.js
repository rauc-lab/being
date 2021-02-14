"use strict";


/**
 * SVG name space string.
 * @constant
 * @type {string}
 */
const SVG_XML_NS = "http://www.w3.org/2000/svg";


/**
 * Spline orders.
 */
const Order = Object.freeze({
    "CUBIC": 4,
    "QUADRATIC": 3,
    "LINEAR": 2,
});


/**
 * Create SVG element.
 */
export function create_element(tag) {
    return document.createElementNS(SVG_XML_NS, tag);
}


/**
 * Set attribute of SVG element.
 */
export function setattr(ele, name, value) {
    ele.setAttributeNS(null, name, value);
}


/**
 * SVG path d attribute string from array of 2d control points.
 * 
 * @param {Array} cps - Bézier control points for one segment. Number of control points defines the curve degree.
 * @returns {string} SVG path d attribute string.
 *
 * Usage:
 *     >>> path_d([[0, 1], [2, 3], [4, 5], [6, 7]])
 *     M0 1 C2 3 4 5 6 7
 */
export function path_d(cps) {
    const order = cps.length;
    if (order == Order.CUBIC) {
        return "M" + cps[0] + "C" + cps.slice(1).flat();
    } else if (order == Order.QUADRATIC) {
        return "M" + cps[0] + "Q" + cps.slice(1).flat();
    } else if (order == Order.LINEAR) {
        return "M" + cps[0] + "L" + cps[1];
    } else {
        throw "Order " + order + " not supported!";
    }
}


export function _draw_path(path, cps) {
    setattr(path, "d", path_d(cps));
}


export function create_path(cps, strokeWidth=1, color="black") {
    const path = create_element("path");
    setattr(path, "stroke", color);
    setattr(path, "stroke-width", strokeWidth);
    setattr(path, "fill", "transparent");
    path.draw = function() {
        _draw_path(path, cps);
    }
    path.draw();
    return path;
}


export function _draw_circle(circle, center) {
    setattr(circle, "cx", center[0]);
    setattr(circle, "cy", center[1]);
}


export function create_circle(center, radius=1, color="red") {
    const circle = create_element("circle");
    setattr(circle, "r", radius);
    setattr(circle, "fill", color);
    circle.draw = function() {
        _draw_circle(circle, center);
    }
    circle.draw();
    return circle;
}


export function _draw_line(line, start, end) {
    setattr(line, "x1", start[0]);
    setattr(line, "y1", start[1]);
    setattr(line, "x2", end[0]);
    setattr(line, "y2", end[1]);
}


export function create_line(start, end, strokeWidth=1, color='black') {
    const line = create_element("line");
    setattr(line, "stroke-width", strokeWidth);
    setattr(line, "stroke", color);
    line.draw = function() {
        _draw_line(line, start, end);
    }
    line.draw();
    return line;
}


/**
 * Draw path from control points onto SVG.
 */
export function draw_path(svg, cps, strokeWidth=1, color='black') {
    const path = create_element('path');
    setattr(path, "d", path_d(cps));
    setattr(path, "stroke", color);
    setattr(path, "stroke-width", strokeWidth);
    setattr(path, "fill", "transparent");
    svg.appendChild(path);
    return path;
}


/**
 * Draw circle onto SVG.
 */
export function draw_circle(svg, center, radius=1, color='red') {
    const [cx, cy] = center;
    const circle = create_element('circle');
    setattr(circle, "cx", cx);
    setattr(circle, "cy", cy);
    setattr(circle, "r", radius);
    setattr(circle, "fill", color);
    svg.appendChild(circle);
    return circle;
}


/**
 * Draw line onto SVG.
 */
export function draw_line(svg, start, end, strokeWidth=1, color='black') {
    const [x1, y1] = start;
    const [x2, y2] = end;
    const line = create_element("line");
    setattr(line, "x1", x1);
    setattr(line, "y1", y1);
    setattr(line, "x2", x2);
    setattr(line, "y2", y2);
    setattr(line, "stroke-width", strokeWidth);
    setattr(line, "stroke", color);
    svg.appendChild(line);
    return line;
}
