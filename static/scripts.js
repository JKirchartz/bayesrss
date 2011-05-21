$(document).ready(function() {
    
    $("div a").click(postClassify(e));
    
);

function addClassifyLinks() {
    $("div.item", this).append("<a action='ham' href='#'>Ham</a>&nbsp;&nbsp;&nbsp;<a action='spam' href='#'>Spam</a>");
}

function postClassify(e) {
    e.preventDefault();
    $.post("/feed/classify", 
        {"feed" : $("#feed").attr("key"),
        "id" : $(this).parent().attr("id"),
        "action" : $(this).attr("action")},
        function(xml) {
        
        }
    );
}
