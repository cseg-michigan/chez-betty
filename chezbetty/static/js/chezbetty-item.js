

keyboard_input = "";
$(document).keypress(function (e) {
	if (e.which == 13) {
		// Got new scan!
		if (keyboard_input.length > 1) {
			console.log("barcode: " + keyboard_input);
			add_item(keyboard_input);
			keyboard_input = "";
		}
	} else {
		keyboard_input += String.fromCharCode(e.which);
	}
});

