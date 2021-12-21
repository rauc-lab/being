/**
 * Editable text field.
 *
 * @module js/editable_text
 */


/**
 * Make text field editable by double clicking it. On change callback is called
 * when user leaves editing mode by hitting enter key. Additionally a validator
 * function can be provided to validate newly generated input text. This
 * validator function can either reformat the text or throw an error. For the
 * latter all changes will be reverted.
 *
 * @param {HTMLElement} ele - Element to make editable.
 * @param {Function} on_change - On change event callback.
 * @param {Function | null} [validator=null] - Text content validator function.
 * @param {boolean} [newLines=false] - If to accept new lines or not.
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
