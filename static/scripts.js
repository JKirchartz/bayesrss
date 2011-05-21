$(document).ready(addClassifyLinks);

function addClassifyLinks() {
    $("div a", this).remove();
    $("div.unclassified", this).append("<a class='classify' action='ham' href='#'>Ham</a>&nbsp;&nbsp;&nbsp;<a action='spam' href='#'>Spam</a>");
    $("div.classified", this).append("<a class='undo' href='#'>Undo</a>");
    $("div a.classify", this).click(postClassify);
    $("div a.undo", this).click(postUndo);
}

function setProbability(response) {
    $(this).toggleClass("unclassified classified");
    addClassifyLinks.apply(this, [response]);
}

function postClassify(e) {
    e.preventDefault();
    $.post("/feed/classify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(this).parent().attr("id"),
        "action" : $(this).attr("action")},
        setProbability
    );
}

function postUndo(e) {
    e.preventDefault();
    $.post("/feed/unclassify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(this).parent().attr("id")},
        setProbability
    );
}
