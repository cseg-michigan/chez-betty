function alert_success (success_str) {
	html = '<div class="alert alert-success" role="alert">'+success_str+'</div>';
	alert_clear();
	$("#alerts").html(html);
}

function alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	alert_clear();
	$("#alerts").html(html);
}

