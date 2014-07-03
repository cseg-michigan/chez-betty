
function clear_input() {
	keyboard_input = "";
}

keyboard_input = "";
$(document).keypress(function (e) {
	clearInterval(input_timer);
	input_timer = setInterval(clear_input, 500);

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
