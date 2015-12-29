var click = false;
var yPos  = 0;

$('html').css('-moz-user-select','none'); // assuming Iceweasel is the browser

$(document).on({
    'mousedown': function(event) {
        click = true;
        yPos  = event.pageY;
    },
    'mousemove': function(event) {
        if(click) $(window).scrollTop( $(window).scrollTop() + (yPos - event.pageY) );
    },
    'mouseup': function() {
        click = false;
    }
});
