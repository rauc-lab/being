function remove_all_children(el) {
    while (el.firstChild) {
        el.removeChild(el.lastChild);
    }
}

function add_option(select, name) {
    const option = document.createElement("option");
    option.setAttribute("value", name);
    option.innerHTML = name;
    select.appendChild(option);
    return option;
}


function name_option(select, index, name) {
    select.children[index].innerHTML = name;
}


function default_names(select, base="Curve") {
    for (let i = 0; i < select.childElementCount; i++) { 
        //text += cars[i] + "<br>";
        name_option(select, i, `${base} ${i + 1}`);
    }
    
    
    /*
    for (const [index, option] of select.children) {
        //option.innerHTML = `${base} ${index + 1}`;
        //name_option(option, base + " " + index);
    }
    */
}



select = document.createElement("select");
add_option(select, 'First');
add_option(select, 'Second');
add_option(select, 'Third');


default_names(select);


/*
for (opt of select.children) {
    console.log(opt);
}
*/
