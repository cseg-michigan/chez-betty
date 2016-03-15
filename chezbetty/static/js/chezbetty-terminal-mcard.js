
// When this gets called
function submit_input () {
	if (keyboard_input.slice(0, 3) == "%B6") {
		// This looks like an M-Card
		umid = keyboard_input.slice(8, 16);

		window.location.replace("/terminal/" + umid);
	}

	keyboard_input = "";
}

keyboard_input = "";
input_timer = null;

$(document).keypress(function (e) {
	alert_clear();

	// Ignore MCard input while the splash screen is live
	if ($('#splash').is(':visible')) return;

	if (input_timer) {
		clearInterval(input_timer);
	}
	input_timer = setInterval(submit_input, 500);

	keyboard_input += String.fromCharCode(e.which);
});
