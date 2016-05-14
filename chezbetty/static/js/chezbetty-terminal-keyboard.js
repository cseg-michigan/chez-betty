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
	if (keyboard_input.slice(0, 3) == "%B6") {
		// This looks like an M-Card
		var umid = keyboard_input.slice(8, 16);

		// Ignore MCard input while the splash screen is live
		if ($('#splash').is(':visible')) {
			keyboard_input = '';
			return;
		}

		window.location.replace("/terminal/" + umid);

	} else if (keyboard_input.length == 7 && keyboard_input.slice(0, 4) == "BILL") {
		if (keyboard_input == 'BILLBEG') {
			// A bill was inserted
			deposit_counting();
		} else {

			// This looks like the bill acceptor
			var dollars = parseInt(keyboard_input.slice(4, 7));

			// Call the main code to actually handle this
			handle_deposit(dollars, 'acceptor');
		}

	} else {
		// Well, this must be a barcode scan
		if (keyboard_input.length > 1) {
			var barcode = keyboard_input.slice(0, keyboard_input.length-1);
			add_item(barcode);
		}
	}

	keyboard_input = '';
}



// Called on each keypress
$(document).keypress(function (e) {
	// Hide any notifications from any previous actions.
	alert_clear();

	// Reset the timeout timer
	if (input_timer) {
		clearInterval(input_timer);
	}
	// Start a new timeout in case this is the last keypress
	input_timer = setInterval(submit_input, 500);

	// Save the character we just got
	keyboard_input += String.fromCharCode(e.which);
});
