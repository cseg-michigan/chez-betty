// single use button

$(".button-showhide").on('click', function () {
	cls = $(this).attr('data-class');
	$('.'+cls).toggle();
	var alt_text = $(this).attr('data-alt-text');
	if ( alt_text != undefined ) {
		var text = $(this).text();
		$(this).text(alt_text);
		$(this).attr('data-alt-text', text);
	}
});

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
		var input  = $(this);
		var save   = $('#' + $(this).attr("id") + '-btn-save'  );
		var revert = $('#' + $(this).attr("id") + '-btn-revert');
		save.hide();
		revert.hide();
		input.attr('data-initial', data["value"]);
		alert_success(data["msg"]);
	} else {
		alert_error(data["msg"]);
	}
}

function button_save_fail (data) {
	alert_error("Error saving changes.");
}

function ajax_button_textlike (js_obj, object, field, id, value) {
	var url = "/admin/ajax/text/"+object+"/"+id+"/"+field;
	$.ajax({
		url: url,
		method: 'POST',
		data: {
			'value' : value,
		},
		context: js_obj,
		success: button_save_success,
		error: button_save_fail
	});
};

$(".ajax-textlike-btn-save").on('click', function () {
	var fields = $(this).attr("id").split("-");
	var input  = $('#' + $(this).attr("id").slice(0,-9));
	var value = input.val();
	ajax_button_textlike(input, fields[2], fields[3], fields[4], value);
});

$(".ajax-textlike-btn-revert").on('click', function () {
	var textarea_id = $(this).attr("id").slice(0,-11);
	var textarea = $('#'+textarea_id);
	textarea.val(textarea.attr('data-initial'));
	textarea.trigger('input');
});

$(".ajax-textlike").on('input', function () {
	var save_btn = $('#' + $(this).attr("id") + '-btn-save');
	var revert_btn = $('#' + $(this).attr("id") + '-btn-revert');
	if ($(this).attr('data-initial') != $(this).val()) {
		save_btn.show();
		revert_btn.show();
	} else {
		save_btn.hide();
		revert_btn.hide();
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

$(".ajax-fill").each(function () {
	$(this).removeClass("ajax-fill");
	$(this).load($(this).attr("data-path"));
});

// Based off http://stackoverflow.com/questions/6112660/
$(".fitin").each(function () {
	var height  = $(this).attr("data-fitin-height");
	var width   = $(this).attr("data-fitin-width");
	var columns = $(this).attr("data-fitin-columns") == "true";

	while ($(this).height() > height) {
		$(this).css('font-size', (parseInt($(this).css('font-size')) - 1) + "px" );

		if (columns) {
			$(this).css('column-count', parseInt($(this).css('column-count')) + 1 );
			$(this).css('-webkit-column-count', parseInt($(this).css('-webkit-column-count')) + 1 );
			$(this).css('-moz-column-count', parseInt($(this).css('-moz-column-count')) + 1 );
		}
	}
});


// Generic JS to disable a controlled element if this input is empty
$('.disable-controlled-when-empty').on('change input', function disable_controlled_on_change() {
	var controlled = $('#' + $(this).attr('data-controlled'));
	var contents = $.trim($(this).val());
	if ( contents == '' ) {
		controlled.prop('disabled', true);
	} else {
		controlled.prop('disabled', false);
	}
});


// Generic JS to verify that all form fields have been filled out
$('.form-with-requirements').submit(function check_submit(evt) {
	evt.preventDefault();

	var missing_requirements = [];
	$('.form-required').each(function check_submit_each(index) {
		$('.form-required-message').hide();
		$(this).removeClass('form-required-missing');
		if ( $(this).is("input") ) {
			if ( $(this).val() == '' ) {
				missing_requirements.push($(this));
			}
		} else if ( $(this).is("select") ) {
			if ( $(this).val() == null ) {
				missing_requirements.push($(this));
			}
		}
	});

	if (missing_requirements.length != 0) {
		$('.form-required-message').show();
		$.each(missing_requirements, function report_missing_requirement(index) {
			$(this).addClass('form-required-missing');
		});
		return false;
	}

	$(this).unbind('submit').trigger('submit');
});


// Item request page hook to selectively validate URL field
$('#request-vendor').change(function() {
	var selected = $(this).find(":selected");
	if ( selected.attr('data-product-urls') == 'True' ) {
		$('#request-vendor-url').addClass('form-required');
	} else {
		$('#request-vendor-url').removeClass('form-required');
		$('#request-vendor-url').removeClass('form-required-missing');
	}
});

