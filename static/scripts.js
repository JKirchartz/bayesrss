$(document).ready(function() {
    addClassifyLinks($(this));
});

function addClassifyLinks(dom) {
    $("a", dom).remove();
    $(".unclassified", dom).append("<a class='classify' action='ham' href='#'>Ham</a>&nbsp;&nbsp;&nbsp;<a class='classify' action='spam' href='#'>Spam</a>");
    $(".classified", dom).append("<a class='undo' href='#'>Undo</a>");
    $("a.classify", dom).click(postClassify);
    $("a.undo", dom).click(postUndo);
}

function setProbability(dom, response) {
    $(dom).toggleClass("unclassified classified");
    addClassifyLinks(dom, response);
}

function postClassify(e) {
    dom = $(this).parent()
    e.preventDefault();
    $.post("/feed/classify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(this).parent().attr("id"),
        "action" : $(this).attr("action")},
        function(response) {
            setProbability(dom, response);
        }
    );
}

function postUndo(e) {
    dom = $(this).parent()
    e.preventDefault();
    $.post("/feed/unclassify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(this).parent().attr("id")},
        function(response) {
            setProbability(dom, response);
        }
    );
}
