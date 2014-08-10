
// Callback when scanner input is detected and read
$("body").bind("scannerDetectionComplete", function (e, data) {
	add_item(data.string);
});

// "Errors" are really just things that didn't turn out to be barcodes
// Add them to currently selected thing
$("body").bind("scannerDetectionError", function (e, data) {
	var focused = $(':focus');
	var cursor_pos = document.getElementById(focused.attr("id")).selectionStart;
	var cursor_end = document.getElementById(focused.attr("id")).selectionEnd;
	var start = focused.val();
	focused.val(start.substring(0, cursor_pos) + data.string + start.substring(cursor_end));

	// Put the cursor back where it was.
	document.getElementById(focused.attr("id")).selectionStart = cursor_pos + data.string.length;
	document.getElementById(focused.attr("id")).selectionEnd = cursor_pos + data.string.length;

	// Trigger the input change
	focused.trigger("input");
});

// Register the scanner detector
$("body").scannerDetection({preventDefault:true});
