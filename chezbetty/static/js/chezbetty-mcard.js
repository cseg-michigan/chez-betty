

keyboard_input = "";
$(document).keypress(function (e) {
	if (e.which == 13) {
		// Got new scan!

		console.log("input: " + keyboard_input);

		if (keyboard_input.slice(0, 3) == "%B6") {
			// This looks like an M-Card
			umid = keyboard_input.slice(8, 16);
			console.log("umid: " + umid);
			window.location.replace("/purchase/" + umid);
		} else {
			console.log("not an mcard?");
		}

		keyboard_input = "";
	} else {
		keyboard_input += String.fromCharCode(e.which);
	}
});

