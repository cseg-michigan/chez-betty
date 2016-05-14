/*
 * Handle all keyboard input on the terminal.
 * This means handle:
 * - MCards
 * - Barcode Scans
 * - Bill Acceptor inputs
 *
 */


// Global state
var keyboard_input = '';
var input_timer = null;


// This gets called when keyboard input stops.
function process_input () {
	// Keep a local copy so we can clear global in case anything goes wrong.
	var keyin = keyboard_input;
	keyboard_input = '';

	if (keyin.slice(0, 3) == "%B6") {
		// This looks like an M-Card
		var umid = keyin.slice(8, 16);

		// Ignore MCard input while the splash screen is live
		if ($('#splash').is(':visible')) {
			return;
		}

		window.location.replace("/terminal/" + umid);

	} else if ((keyin.length == 7 || keyin.length == 14) &&
		       keyin.slice(0, 4) == "BILL") {
		// This looks like the bill acceptor.
		// We handle either two separate messages (BEG and amount) or them
		// as one string.
		var dollars = keyin.slice(keyin.length-3, keyin.length);

		if (dollars == 'BEG') {
			start_deposit();
		} else {
			// Call the main code to actually handle this
			handle_deposit(parseInt(dollars), 'acceptor');
		}

	} else {
		// Well, this must be a barcode scan
		if (keyin.length > 1) {
			var barcode = keyin.slice(0, keyin.length-1);
			add_item(barcode);
		}
	}
}



// Called on each keypress
$(document).keypress(function (e) {
	// Hide any notifications from any previous actions.
	alert_clear();

	// Reset the timeout timer
	if (input_timer) {
		clearTimeout(input_timer);
	}
	// Start a new timeout in case this is the last keypress
	input_timer = setTimeout(process_input, 500);

	// Save the character we just got
	keyboard_input += String.fromCharCode(e.which);
});
