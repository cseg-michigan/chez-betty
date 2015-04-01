// single use button

function button_singleuse_success (data) {
	if (data["status"] == "success") {
		$(this).hide();
		alert_success(data["msg"]);
	} else {
		alert_error(data["msg"]);
	}
}

function button_singleuse_fail (data) {
	alert_error("Button click failed.");
}

$(".btn-ajax_singleuse").on('click', function () {
	var url = $(this).attr("data-url");
	$.ajax({
		url: url,
		context: $(this),
		success: button_singleuse_success,
		error: button_singleuse_fail
	});
});

