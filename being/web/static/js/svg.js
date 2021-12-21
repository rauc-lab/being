/**
 * Working with SVG elements.
 * @module js/svg
 */
import {Order} from "/static/js/spline.js";


/** @const {string} SVG name space string. */
const SVG_XML_NS = "http://www.w3.org/2000/svg";


/**
 * Create SVG element.
 * @param {string} tag - SVG element tag name.
 * @returns {SVGElement} Freshly created SVG element.
 */
export function create_element(tag) {
    return document.createElementNS(SVG_XML_NS, tag);
}


/**
 * Set attribute of SVG element.
 * @param {SVGElement} ele - SVG element.
 * @param {string} name - Attribute name.
 * @param {number|string} value - Attribute value.
 */
export function setattr(ele, name, value) {
    ele.setAttributeNS(null, name, value);
}

/**
 * Get attribute of SVG element. 
 * @param {SVGElement} ele - SVG element.
 * @param {String} name - Attribute name.
 * @returns {number|string} Attribute value.
 */
export function getattr(ele, name) {
    return ele.getAttributeNS(null, name);
}


/**
 * SVG path d attribute string from array of 2d control points.
 * 
 * @param {array} cps - Bézier control points for one segment. Number of
 *     control points defines the curve degree.
 * @returns {string} SVG path d attribute string.
 *
 * @example
 * // returns "M0 1 C2 3 4 5 6 7"
 * path_d([[0, 1], [2, 3], [4, 5], [6, 7]]);
 */
export function path_d(cps) {
    const order = cps.length;
    switch (order) {
        case Order.CUBIC:
            return "M" + cps[0] + "C" + cps.slice(1).flat();
        case Order.QUADRATIC:
            return "M" + cps[0] + "Q" + cps.slice(1).flat();
        case Order.LINEAR:
            return "M" + cps[0] + "L" + cps[1];
        default:
            throw "Order " + order + " not supported!";
    }
}


/**
 * Draw control points as path onto SVG.
 * @param {SVGElement} svg - Target SVG element.
 * @param {array} cps - Control points.
 * @param {number} [strokeWidth=1] - Stroke width.
 * @param {string} [color=black] - Stroke color.
 * @returns {SVGPathElement} New SVG path element.
 */
export function draw_path(svg, cps, strokeWidth = 1, color = "black") {
    const path = create_element("path");
    setattr(path, "d", path_d(cps));
    setattr(path, "stroke", color);
    setattr(path, "stroke-width", strokeWidth);
    setattr(path, "fill", "transparent");
    svg.appendChild(path);
    return path;
}


/**
 * Draw circle onto SVG.
 * @param {SVGElement} svg - Target SVG element.
 * @param {array} center - Circle center.
 * @param {number} [radius=1] - Circle radius.
 * @param {string} [color=red] - Fill color.
 * @returns {SVGCircleElement} New SVG circle element.
 */
export function draw_circle(svg, center, radius = 1, color = "red") {
    const [cx, cy] = center;
    const circle = create_element("circle");
    setattr(circle, "cx", cx);
    setattr(circle, "cy", cy);
    setattr(circle, "r", radius);
    setattr(circle, "fill", color);
    svg.appendChild(circle);
    return circle;
}


/**
 * Draw line onto SVG.
 * @param {SVGElement} svg - Target SVG element.
 * @param {array} start - Start point.
 * @param {array} end - End point.
 * @param {number} [strokeWidth=1] - Stroke width.
 * @param {string} [color=black] - Stroke color.
 * @returns {SVGLineElement} New SVG circle element.
 */
export function draw_line(svg, start, end, strokeWidth = 1, color = "black") {
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
