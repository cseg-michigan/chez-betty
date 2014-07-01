

function clear_spinner () {
	$(".spinner").remove();
	$("#index-main").show();
	$("#front-buttons").show();
	alert_error("Error while logging in. Please try again.");
}

keyboard_input = "";
$(document).keypress(function (e) {
	alert_clear();

	if (e.which == 37) {
		// got percent character. show spinner

		$("#index-main").hide();
		$("#front-buttons").hide();

		// Display spinner in case loading the user takes a while.
		var opts = {
		  lines: 11, // The number of lines to draw
		  length: 18, // The length of each line
		  width: 9, // The line thickness
		  radius: 19, // The radius of the inner circle
		  corners: 1, // Corner roundness (0..1)
		  rotate: 0, // The rotation offset
		  direction: 1, // 1: clockwise, -1: counterclockwise
		  color: '#000', // #rgb or #rrggbb or array of colors
		  speed: 1, // Rounds per second
		  trail: 60, // Afterglow percentage
		  shadow: false, // Whether to render a shadow
		  hwaccel: false, // Whether to use hardware acceleration
		  className: 'spinner', // The CSS class to assign to the spinner
		  zIndex: 2e9, // The z-index (defaults to 2000000000)
		  top: '50%', // Top position relative to parent
		  left: '50%' // Left position relative to parent
		};
		var spinner_location = document.getElementById('spinner-box');
		var spinner = new Spinner(opts).spin(spinner_location);

		setTimeout(clear_spinner, 20*1000);

	} else if (e.which == 94) {
		// Got new scan!

		if (keyboard_input.slice(0, 3) == "%B6") {
			// This looks like an M-Card
			umid = keyboard_input.slice(8, 16);

			window.location.replace("/purchase/" + umid);
		}

		keyboard_input = "";
	} else {
		keyboard_input += String.fromCharCode(e.which);
	}
});

