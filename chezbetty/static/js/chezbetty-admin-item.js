
// Callback when scanner input is detected and read
$("#scanner").bind("scannerDetectionComplete", function (e, data) {
	add_item(data.string);
})

// Register the scanner detector
$("#scanner").scannerDetection();
