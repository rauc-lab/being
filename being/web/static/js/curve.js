import {BPoly} from "/static/js/spline.js";


export class Curve {
    constructor(splines) {
        this.splines = splines;
    }

    static from_object(dct) {
        const splines = dct.splines.map(BPoly.from_object);
        return new Curve(splines);
    }

    to_object() {
        const splines = this.splines.map(spline => {
            return spline.to_dict();
        });

        return {
            "type": "Curve",
            "splines": splines,
        }
    }
};
