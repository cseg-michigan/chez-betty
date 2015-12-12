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

function change_rotating_div(showing_div) {
	var id = showing_div.attr('id');
	var idx = id.split('-').slice(-1)[0];

	var div_root = id.slice(0, -idx.length);
	var next_div = div_root + (parseInt(idx) + 1);
	var j_next_div = $('#'+next_div);

	// .length is jquery idiom for 'selector exists?'
	if (! j_next_div.length) {
		j_next_div = $('#' + div_root + '1');
	}

	showing_div.hide();
	j_next_div.show();

	setTimeout(function() {
		change_rotating_div(j_next_div);
	}, parseInt(showing_div.attr('data-rotate-div-timeout')));
}

$(".rotate-divs").each(function () {
	var showing_div = $(this);
	setTimeout(function() {
		change_rotating_div(showing_div);
	}, parseInt(showing_div.attr('data-rotate-div-timeout')));
});

