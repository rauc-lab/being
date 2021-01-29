"use strict";
const SVG_XML_NS = "http://www.w3.org/2000/svg";


/**
 * Create SVG element.
 */
function create_element(tag) {
    return document.createElementNS(SVG_XML_NS, tag);
}


function setattr(ele, name, value) {
    ele.setAttributeNS(null, name, value);
}


/**
 * SVG path d attribute string from array of 2d control points.
 */
function path_d(cps) {
    const order = cps.length;
    if (order == 4) {
        return "M" + cps[0] + "C" + cps.slice(1).flat();
    } else if (order == 3) {
        return "M" + cps[0] + "Q" + cps.slice(1).flat();
    } else if (order == 2) {
        return "M" + cps[0] + "L" + cps[1];
    } else {
        throw "Order " + order + " not supported!";
    }
}


function draw_path(svg, cps, strokeWidth=1, color='black') {
    const path = create_element('path');
    setattr(path, "d", path_d(cps));
    setattr(path, "stroke", color);
    setattr(path, "stroke-width", strokeWidth);
    setattr(path, "fill", "transparent");
    svg.appendChild(path);
    return;
}


function draw_circle(svg, center, radius=1, color='red') {
    const [cx, cy] = center;
    const circle = create_element('circle');
    setattr(circle, "cx", cx);
    setattr(circle, "cy", cy);
    setattr(circle, "r", radius);
    setattr(circle, "fill", color);
    svg.appendChild(circle);
}


function draw_line(svg, start, end, strokeWidth=1, color='black') {
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
}


export {create_element, path_d, draw_path, draw_circle, draw_line};
