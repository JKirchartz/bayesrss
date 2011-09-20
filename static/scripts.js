$(document).ready(function() {
    addClassifyLinks($(this));
});

function addClassifyLinks(dom) {
    $("div.unclassified", dom).html("<a class='classify' action='ham' href='#'>Ham</a>&nbsp;&nbsp;&nbsp;<a class='classify' action='spam' href='#'>Spam</a>");
    $("div.classified", dom).html("<a class='undo' href='#'>Undo</a>");
    $("a.classify", dom).click(postClassify);
    $("a.undo", dom).click(postUndo);
}

function setProbability(dom, response) {
    $("div.link", dom).toggleClass("unclassified classified");
    addClassifyLinks(dom);
    $("div.prob", dom).html("<b>Prob:</b> " + response)
}

function postClassify(e) {
    dom = $(this).parent().parent()
    e.preventDefault();
    $.post("/feed/classify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(dom).attr("id"),
        "action" : $(this).attr("action")},
        function(response) {
            setProbability(dom, response);
        }
    );
}

function postUndo(e) {
    dom = $(this).parent().parent()
    e.preventDefault();
    $.post("/feed/unclassify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(dom).attr("id")},
        function(response) {
            setProbability(dom, response);
        }
    );
}

