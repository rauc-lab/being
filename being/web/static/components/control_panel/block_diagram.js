/**
 * Block diagram functionality for control panel. Relies on the third-party
 * library `elkjs <https://github.com/kieler/elkjs>`_. Renders being block
 * diagram to the :class:`components/control_panel/control_panel.ControlPanel`
 * widget.
 *
 * @module components/control_panel/block_diagram
 */
import { deep_copy, remove_all_children, } from "/static/js/utils.js";
import { create_element, path_d, setattr, } from "/static/js/svg.js";
import { subtract_arrays, add_arrays, } from "/static/js/array.js";


/** 
 * @constant {object} The 4x possible incoming / outgoing directions of a
 * connection.
 */
const Direction = Object.freeze({
    "NORTH": 0,
    "WEST": 1,
    "SOUTH": 2,
    "EAST": 3,
});


/** @constant {string} SVG CSS styling for block diagram. */
const BLOCK_DIAGRAM_SVG_STYLE = `
    .block rect {
        stroke: black;
        stroke-width: 2;
        fill: none;
    }

    .block text {
        text-anchor: middle;
        alignment-baseline: central;
        font-size: 0.6em;
    }

    path.connection {
        fill: none;
        stroke: black;
        stroke-width: 2;
        marker-end: url(#arrowhead);
    }

    path.connection.value {
        stroke-dasharray: 5;
        animation: dash 1.7s infinite linear;
    }

    @keyframes dash {
        to {
            stroke-dashoffset: -50;
        }
    }

    circle.moving-dot {
        fill: red;
        opacity: 0;
        r: 5;
    }
`;


/**
 * Convert a point object to 2D array.
 *
 * @param {Object} pt - Point object.
 *
 * @returns {array} 2D array.
 */
function pt_to_array(pt) {
    return [pt.x, pt.y];
}


/**
 * Generate marker definition #arrowhead for SVG.
 * Taken from here: http://thenewcode.com/1068/Making-Arrows-in-SVG
 *
 * @returns {SVGMarkerElement} SVG marker definition.
 */
function arrow_marker_definition() {
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
    return marker
}


/**
 * Draw a ELK layout block node on a SVG. Drawn as rectangle with the node's
 * name inside.
 *
 * @param {SVGElement} svg - SVG HTML element to draw on.
 * @param {Object} node - Node object from ELK layout graph.
 *
 * @returns SVG group element representing the node.
 */
function draw_block_node(svg, block) {
    const g = create_element("g");
    g.classList.add("block");

    setattr(g, "transform", "translate(" + block.x + " " + block.y + ")")

    const rect = create_element("rect");
    setattr(rect, "width", block.width);
    setattr(rect, "height", block.height);

    g.appendChild(rect);

    const text = create_element("text");

    setattr(text, "dx", block.width / 2);
    setattr(text, "dy", block.height / 2);
    text.innerHTML = block.name;
    g.appendChild(text);

    svg.appendChild(g);
    return g;
}


/**
 * Calculate cubic SVG path d string for a curvy line connecting two points.
 *
 * @param {array} start - Start point.
 * @param {Direction} startDir - Start direction.
 * @param {array} end - 2d end point.
 * @param {Direction} endDir - End direction.
 *
 * @returns SVG cubic path string.
 */
function curvy_path_d(start, startDir, end, endDir) {
    // Offset vectors for each of the 4x possible connection direction
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
    return path_d(cps);
}


/**
 * Attache a moving dot animation to the SVG element. Along a path.
 *
 * @param {SVGElement} svg - SVG element.
 * @param {String} d - SVG path string.
 * @param {Number} duration - Moving dot animation duration.
 *
 * @returns {Object} Object with attached trigger function to start the
 *     animation.
 */
function attach_moving_dot_animation(svg, d, duration=0.4) {
    const circle = create_element("circle");
    circle.classList.add("moving-dot");

    const pathAnim = create_element("animateMotion");
    setattr(pathAnim, "path", d);
    setattr(pathAnim, "begin", "indefinite");
    setattr(pathAnim, "dur", duration + "s");
    setattr(pathAnim, "fill", "freeze");
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
 * Given a point on the edge of a ELK block, determine the connection
 * direction. Does the connection go NORTH, WEST, SOUTH or EAST?
 *
 * @param {array} pt - 2d edge point.
 * @param {Object} child - ELK layout graph node.
 *
 * @returns {Direction} Connection direction.
 */
function determine_connection_direction(pt, block) {
    // TODO: More sophisticated connection direction which also work for points
    // which do not lay on child's edge.
    const [x, y] = pt;
    if (x === block.x) {
        return Direction.WEST;
    } else if (x === block.x + block.width) {
        return Direction.EAST;
    } else if (y === block.y) {
        return Direction.NORTH;
    } else if (y === block.y + block.height) {
        return Direction.SOUTH;
    }

    throw "Could not determine connection direction. pt " + pt + " not laying on block!";
}


/**
 * Calculate curvy SVG path from elk edge section.
 *
 * @param {?} section ?
 * @param {Object} lookup Block id -> block object lookup.
 * @returns Cubic curvy SVG path string.
 */
function get_connection_path_from_section(section, lookup) {
    const start = pt_to_array(section.startPoint);
    const incoming = lookup[section.incomingShape];
    const startDir = determine_connection_direction(start, incoming);
    const end = pt_to_array(section.endPoint);
    const outgoing = lookup[section.outgoingShape];
    const endDir = determine_connection_direction(end, outgoing);
    return curvy_path_d(start, startDir, end, endDir);
}


/**
 * Draw block diagram graph on SVG. Also prepares the animations inside.
 * Returns an array with all value and message connections. These references
 * can then be used to trigger / steer animations.
 *
 * @param {SVGElement} svg - SVG element to draw on.
 * @param {Object} graph - Block network graph.
 *
 * @returns {array} All value and message connections.
 */
export async function draw_block_diagram(svg, graph) {
    const layout = deep_copy(graph);
    layout.children.forEach(block => {
        block.width = 120;
        block.height = 60;
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
    layout.children.forEach(block => {
        lookup[block.id] = block;
    });

    remove_all_children(svg);

    // Adjust viewBox
    const viewBox = [layout.x, layout.y, layout.width, layout.height].join(" ");
    setattr(svg, "viewBox", viewBox);

    // Add definitions to SVG
    const defs = create_element("defs");
    const marker = arrow_marker_definition();
    defs.appendChild(marker);
    const style = create_element("style");
    setattr(style, "type", "text/css");
    style.innerHTML = BLOCK_DIAGRAM_SVG_STYLE;
    defs.appendChild(style);
    svg.appendChild(defs);

    // Draw blocks
    layout.children.forEach(node => {
        draw_block_node(svg, node);
    });

    // Draw edges / connections lines
    const messageConnections = [];
    const valueConnections = [];
    layout.edges.forEach(edge => {
        edge.sections.forEach(section => {
            const path = create_element("path");
            path.classList.add("connection");
            const d = get_connection_path_from_section(section, lookup);
            setattr(path, "d", d);
            if (edge.connectionType === "message") {
                path.classList.add("message");
                const anim = attach_moving_dot_animation(svg, d);
                messageConnections.push({
                    "index": edge.index,
                    "trigger": anim.trigger,
                });
            } else {
                path.classList.add("value");
                valueConnections.push({
                    "index": edge.index,
                    "play": () => {
                        path.style.animationPlayState = "running";
                    },
                    "pause": () => {
                        path.style.animationPlayState = "paused";
                    },
                });
            }
            svg.appendChild(path);
        });
    });

    return [valueConnections, messageConnections];
}
