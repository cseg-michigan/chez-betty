/*
  JavaScript for Handling a Barcode Scan
*/

var keyboard_input = "";
var input_timer = null;
$(document).keypress(function (e) {
	if (input_timer) {
		clearInterval(input_timer);
	}
	input_timer = setInterval(function () {
		keyboard_input = '';
	}, 500);

	if (e.which == 13) {
		// Got new scan!
		if (keyboard_input.length > 1) {
			add_item(keyboard_input);
			keyboard_input = "";
		}
	} else {
		keyboard_input += String.fromCharCode(e.which);
	}
});
