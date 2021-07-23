/**
 * Block diagram functionality for control panel. Assumes the following
 * third-party Javascript libraries are loaded:
 *   - ELK
 */

import {deep_copy, remove_all_children} from "/static/js/utils.js";
import {create_element, setattr} from "/static/js/svg.js";
import {subtract_arrays, add_arrays} from "/static/js/array.js";


const STROKE_WIDTH = 2;
const Direction = Object.freeze({
    "NORTH": 0,
    "WEST": 1,
    "SOUTH": 2,
    "EAST": 3,
});

/**
 * Convert a pont object into a 2d array.
 *
 * @param {Obect} pt Point object.
 * @returns 2d point array.
 */
function pt_to_array(pt) {
    return [pt.x, pt.y];
}


/**
 * Add marker definition (#arrowhead) to SVG.
 * Taken from here: http://thenewcode.com/1068/Making-Arrows-in-SVG
 *
 * @param {?} svg SVG HTML element.
 */
function add_arrow_marker_definition(svg) {
    const defs = create_element("defs");
    const marker = create_element("marker");
    setattr(marker, "id", "arrowhead");
    setattr(marker, "markerWidth", 10);
    setattr(marker, "markerHeight", 7);
    //setattr(marker, "refX", 10);  // Original arrow
    setattr(marker, "refX", 6.5);
    setattr(marker, "refY", 3.5);
    setattr(marker, "orient", "auto");

    const polygon = create_element("polygon");
    //setattr(polygon, "points", "0 0, 10 3.5, 0 7");  // Original arrow
    setattr(polygon, "points", "0 0, 7 3.5, 0 7");

    marker.appendChild(polygon);
    defs.appendChild(marker);
    svg.appendChild(defs);
}


/**
 * Draw a ELK layout node on a SVG. Also draw a text with the name.
 *
 * @param {?} svg SVG HTML element.
 * @param {Object} child Node object from ELK layout graph.
 * @returns SVG group element representing the block.
 */
function draw_block(svg, child) {
    const g = create_element("g");
    setattr(g, "transform", "translate(" + child.x + " " + child.y + ")")
    svg.appendChild(g);

    const rect = create_element("rect");
    setattr(rect, "width", child.width);
    setattr(rect, "height", child.height);
    setattr(rect, "stroke", "black");
    setattr(rect, "stroke-width", STROKE_WIDTH);
    setattr(rect, "fill", "none");
    g.appendChild(rect);

    const text = create_element("text");
    setattr(text, "text-anchor", "middle");
    setattr(text, "alignment-baseline", "central");
    setattr(text, "dx", child.width / 2);
    setattr(text, "dy", child.height / 2);
    text.innerHTML = child.name;
    g.appendChild(text);

    return g;
}


/**
 * Draw a staight line on a SVG.
 *
 * @param {?} svg SVG HTML element.
 * @param {Array} start 2d start point.
 * @param {Array} end 2d end point.
 * @returns SVG line element.
 */
function draw_line(svg, start, end) {
    const [x1, y1] = start;
    const [x2, y2] = end;
    const line = create_element("line");
    setattr(line, "x1", x1);
    setattr(line, "y1", y1);
    setattr(line, "x2", x2);
    setattr(line, "y2", y2);
    setattr(line, "stroke", "black");
    setattr(line, "stroke-width", STROKE_WIDTH);
    svg.appendChild(line);
    return line;
}


function curvy_path(start, startDir, end, endDir) {
    // Offset vectors for each 4x possible connection direction
    const offsets = {};
    const [dx, dy] = subtract_arrays(end, start);
    offsets[Direction.NORTH] = [0, -dy];
    offsets[Direction.EAST] = [dx, 0];
    offsets[Direction.SOUTH] = [0, dy];
    offsets[Direction.WEST] = [-dx, 0];

    // Curvy cubic path
    const cps = [
        start,
        add_arrays(start, offsets[startDir]),
        add_arrays(end, offsets[endDir]),
        end,
    ];
    return "M" + cps[0] + "C" + cps.slice(1).flat();
}


function attach_moving_dot_animation(svg, d, duration=0.4) {
    const circle = create_element("circle");
    setattr(circle, "r", 5);
    setattr(circle, "fill", "red");
    setattr(circle, "opacity", "0");

    const pathAnim = create_element("animateMotion");
    setattr(pathAnim, "begin", "indefinite");
    setattr(pathAnim, "dur", duration + "s");
    setattr(pathAnim, "fill", "freeze");
    setattr(pathAnim, "path", d);
    circle.appendChild(pathAnim);

    const opacityAnim = create_element("animate");
    setattr(opacityAnim, "attributeName", "opacity");
    setattr(opacityAnim, "begin", "indefinite");
    setattr(opacityAnim, "dur", duration + "s");
    setattr(opacityAnim, "fill", "freeze");
    setattr(opacityAnim, "keyTimes", "0; .5; 1");
    setattr(opacityAnim, "values", "0; 1; 0");

    circle.appendChild(opacityAnim);
    svg.appendChild(circle);

    return {
        trigger: () => {
            pathAnim.beginElement();
            opacityAnim.beginElement();
        }
    }
}


/**
 * Determine the connection direction on a ELK block node. Does the connection
 * go NORTH, WEST, SOUTH or EAST?
 *
 * @param {Array} pt 2d point.
 * @param {Object} child ELK layout graph node.
 * @returns Connection direction.
 */
function determine_connection_direction(pt, child) {
    // TODO: More sophisticated connection direction which also work for points
    // which do not lay on child's edge.
    const [x, y] = pt;
    if (x === child.x) {
        return Direction.WEST;
    } else if (x === child.x + child.width) {
        return Direction.EAST;
    } else if (y === child.y) {
        return Direction.NORTH;
    } else if (y === child.y + child.height) {
        return Direction.SOUTH;
    }

    throw "Could not determine connection direction. pt " + pt + " not laying on child!";
}

/**
 * Draw block diagram on SVG.
 *
 * @param {?} svg SVG element to draw to.
 * @param {Object} graph Block network graph.
 */
export async function draw_block_diagram(svg, graph) {
    const layout = deep_copy(graph);
    layout.children.forEach(child => {
        child.width = 120;
        child.height = 60;
    })
    layout.id = "root";
    const elk = new ELK();
    await elk.layout(layout, {
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.layered.spacing.nodeNodeBetweenLayers": 50,
            //"elk.edgeRouting": "ORTHOGONAL",
            //"elk.layered.spacing.edgeNodeBetweenLayers": "30",
            //"elk.algorithm": "graphviz.dot",
        }
    });

    const lookup = {};
    layout.children.forEach(child => {
        lookup[child.id] = child;
    });
    remove_all_children(svg);
    add_arrow_marker_definition(svg)
    layout.children.forEach(child => {
        draw_block(svg, child);
    });

    const messageConnections = [];

    layout.edges.forEach(edge => {
        edge.sections.forEach(section => {
            const start = pt_to_array(section.startPoint);
            const end = pt_to_array(section.endPoint);
            const incoming = lookup[section.incomingShape];
            const outgoing = lookup[section.outgoingShape];
            const startDir = determine_connection_direction(start, incoming);
            const endDir = determine_connection_direction(end, outgoing);
            const d = curvy_path(start, startDir, end, endDir);

            const path = create_element("path");
            svg.appendChild(path);
            setattr(path, "d", d);
            setattr(path, "fill", "none");
            setattr(path, "stroke", "black");
            setattr(path, "stroke-width", STROKE_WIDTH);
            if (edge.connectionType === "message") {
                setattr(path, "stroke-dasharray", "5,5");
                const anim = attach_moving_dot_animation(svg, d);
                messageConnections.push({
                    "index": edge.index,
                    "trigger": anim.trigger,
                });
            } else {
                //setattr(path, "marker-end", "url(#arrowhead)");
                //connections.push({ "index": edge.index, "path": path, });
            }
        });
    });

    // Adjust viewBox
    const viewBox = [layout.x, layout.y, layout.width, layout.height].join(" ");
    setattr(svg, "viewBox", viewBox);

    return messageConnections;
}
