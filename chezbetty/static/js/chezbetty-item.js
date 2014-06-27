

keyboard_input = "";
$(document).keypress(function (e) {
	if (e.which == 13) {
		// Got new scan!
		console.log("barcode: " + barcode);
		add_item(barcode);
		keyboard_input = "";
	}
	keyboard_input += String.fromCharCode(e.which);
});

