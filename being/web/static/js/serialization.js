import { BPoly } from "/static/js/spline.js";
import { Curve } from "/static/js/curve.js";


/**
 * Create being object from JS dictionary object. 
 */
export function objectify(dct) {
    switch (dct["type"]) {
        case "BPoly":
            return BPoly.from_dict(dct);
        case "Curve":
            return Curve.from_dict(dct);
        default:
            throw `Can not objectify ${dct["type"]}`;
    }
}


export function anthropomorphify(obj) {
    return obj.to_dict();
}
