/**
 * Serializing and deserializing splines and curve objects.
 * @module js/serialization
 */
import { BPoly } from "/static/js/spline.js";
import { Curve } from "/static/js/curve.js";


/**
 * Create being object from JS dictionary object. 
 * @param {object} dct - Dictionary representation.
 * @returns Being object.
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


/**
 * Convert being object to object representation.
 * @param {object} obj - Being object.
 * @returns {object} Dictionary representation.
 */
export function anthropomorphify(obj) {
    return obj.to_dict();
}
