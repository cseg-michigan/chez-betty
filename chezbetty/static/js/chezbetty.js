/* Functions to display and hide alerts at the top of the page
 */

function alert_clear () {
	$("#alerts").empty();
}

function alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	$("#alerts").empty();
	$("#alerts").html(html);
}

function enable_button (button) {
	button.removeAttr("disabled");
}

function disable_button (button) {
	button.attr("disabled", "disabled");
}

