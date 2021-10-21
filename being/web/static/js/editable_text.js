/**
 * Make text field editable by double clicking it.
 * 
 * @param {*} ele Element to make editable.
 * @param {*} on_change On change event callback.
 * @param {*} validator Text content validator function.
 * @param {*} newLines If to accept new lines or not.
 */
export function make_editable(ele, on_change, validator=null, newLines=false) {
    if (validator === null) {
        validator = value => { return value; }
    }

    ele.contentEditable = false;  // "false" prevents text syntax highlighting
    ele.title = "Double click to edit";
    ele.style.cursor = "text";
    //ele.setAttribute("required", "");
    ele.addEventListener("dblclick", evt => {
        ele.contentEditable = true;
        ele.focus();
    });

    let oldValue = null;
    function capture() {
        oldValue = ele.innerText;
    }

    function revert() {
        ele.innerText = oldValue;
    }

    ele.addEventListener("focus", evt => {
        capture();
    });

    ele.addEventListener("blur", evt => {
        ele.contentEditable = false;
    })

    ele.addEventListener("keyup", evt => { 
        if (evt.key === "Escape") {
            revert();
            ele.blur();
        } else if (evt.key === "Enter") {
            try {
                const validated = validator(ele.innerText);
                if (validated === undefined) {
                    throw "Validator returned undefined!";
                }

                if (validated === oldValue) {
                    throw "No change!";
                }

                // TODO: Swap order? But value should be changed before
                // emitting?
                ele.innerText = validated;
                on_change(validated);
            }
            catch {
                revert();
            }
            finally {
                ele.blur();
            }
        }
    });

    if (!newLines) {
        ele.addEventListener("keypress", evt => {
            if (evt.key === "Enter") {
                evt.preventDefault();
            }
        })
    }
}
