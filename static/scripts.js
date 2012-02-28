$(document).ready(function() {
    addClassifyLinks($(this));
});

function addClassifyLinks(dom) {
    $("div.unclassified", dom).html(
        "<a class='classify button icon approve' action='ham' href='#'>Ham</a> \
        <a class='classify button icon remove' action='spam' href='#'>Spam</a>");
    $("div.classified", dom).html("<a class='undo button icon arrowleft' href='#'>Undo</a>");
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

