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

function button_save_success (data) {
	if (data["status"] == "success") {
		var input = $('#' + $(this).attr("id").slice(0,-4) + '-input');
		$(this).hide();
		input.attr('data-initial', data["value"]);
		alert_success(data["msg"]);
	} else {
		alert_error(data["msg"]);
	}
}

function button_save_fail (data) {
	alert_error("Button save failed.");
}

$(".btn-ajax_savefield").on('click', function () {
	var url = $(this).attr("data-url");
	var id = $(this).attr("id").slice(0,-4);
	var input = $('#' + $(this).attr("id").slice(0,-4) + '-input');
	$.ajax({
		url: url,
		method: 'POST',
		data: {
			'pool' : id,
			'name' : input.val(),
		},
		context: $(this),
		success: button_save_success,
		error: button_save_fail
	});
});

$(".input-ajax_savefield").on('input', function () {
	var btn = $('#' + $(this).attr("id").slice(0,-6) + '-btn');
	if ($(this).attr('data-initial') != $(this).val()) {
		btn.show();
	} else {
		btn.hide();
	}
});

