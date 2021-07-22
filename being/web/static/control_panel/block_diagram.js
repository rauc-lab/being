/**
 * Block diagram drawing. Assumes the following third-party Javascript libraries are loaded:
 *   - ELK
 */

import {deep_copy, remove_all_children} from "/static/js/utils.js";
import {create_element, setattr} from "/static/js/svg.js";
import {BBox} from "/static/js/bbox.js";
import {subtract_arrays} from "/static/js/array.js";


/*
 * From here: http://thenewcode.com/1068/Making-Arrows-in-SVG
 */
function add_arrow_marker_definition(svg) {

    const defs = create_element("defs");
    const marker = create_element("marker");
    setattr(marker, "id", "arrowhead");
    setattr(marker, "markerWidth", 10);
    setattr(marker, "markerHeight", 7);
    //setattr(marker, "refX", 10);  // Original arrow
    setattr(marker, "refX", 7);
    setattr(marker, "refY", 3.5);
    setattr(marker, "orient", "auto");

    const polygon = create_element("polygon");
    //setattr(polygon, "points", "0 0, 10 3.5, 0 7");  // Original arrow
    setattr(polygon, "points", "0 0, 7 3.5, 0 7");

    marker.appendChild(polygon);
    defs.appendChild(marker);
    svg.appendChild(defs);
}


function draw_block(svg, child) {
    const g = create_element("g");
    setattr(g, "transform", "translate(" + child.x + " " + child.y + ")")
    svg.appendChild(g);

    const rect = create_element("rect");
    setattr(rect, "width", child.width);
    setattr(rect, "height", child.height);
    setattr(rect, "stroke", "black");
    setattr(rect, "stroke-width", 2);
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


function draw_line(svg, start, end) {
    const [x1, y1] = start;
    const [x2, y2] = end;
    const line = create_element("line");
    setattr(line, "x1", x1);
    setattr(line, "y1", y1);
    setattr(line, "x2", x2);
    setattr(line, "y2", y2);
    setattr(line, "stroke", "black");
    setattr(line, "stroke-width", 2);
    svg.appendChild(line);
    return line;
}


function pt_to_array(pt) {
    return [pt.x, pt.y];
}


export async function draw_block_diagram(svg, graph) {
    const elkGraph = deep_copy(graph);
    elkGraph.children.forEach(child => {
        child.width = 120;
        child.height = 60;
    })

    // Layout graph
    elkGraph.id = "root";
    let elk = new ELK();
    await elk.layout(elkGraph, {
        layoutOptions: {
            "elk.algorithm": "layered",
            "elk.layered.spacing.nodeNodeBetweenLayers": 50,
            //"elk.edgeRouting": "ORTHOGONAL",
            //"elk.layered.spacing.edgeNodeBetweenLayers": "30",
            //"elk.algorithm": "graphviz.dot",
        }
    });

    const bbox = new BBox();
    remove_all_children(svg);
    add_arrow_marker_definition(svg)
    elkGraph.children.forEach(child => {
        draw_block(svg, child);
        bbox.expand_by_point([child.x, child.y]);
        bbox.expand_by_point([child.x + child.width, child.y + child.height]);
    });
    elkGraph.edges.forEach(edge => {
        edge.sections.forEach(section => {
            const start = pt_to_array(section.startPoint);
            const end = pt_to_array(section.endPoint);
            const line = draw_line(svg, start, end);
            setattr(line, "marker-end", "url(#arrowhead)");
            bbox.expand_by_points([start, end]);
        });
    });

    console.log(bbox.ll, bbox.size)
    const [x, y] = bbox.ll;
    const [w, h] = bbox.size;
    const m = 20;
    const viewBox = [x-m, y-m, w+2*m, h+2*m].join(" ");
    setattr(svg, "viewBox", viewBox);
}
