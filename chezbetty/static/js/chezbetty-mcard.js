

keyboard_input = "";
$(document).keypress(function (e) {
	if (e.which == 13) {
		// Got new scan!

		if (keyboard_input.slice(0, 3) == "%B6") {
			// This looks like an M-Card
			umid = keyboard_input.slice(8, 16);

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
			var spinner_location = document.getElementById('login-panel');
			var spinner = new Spinner(opts).spin(spinner_location);

			window.location.replace("/purchase/" + umid);
		}

		keyboard_input = "";
	} else {
		keyboard_input += String.fromCharCode(e.which);
	}
});

