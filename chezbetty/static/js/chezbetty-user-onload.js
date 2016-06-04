
$(".date").each(function (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
});

// Make checkboxes bootstrappy
$(".user-switch").bootstrapSwitch();

function ajax_bool (js_obj, object, field, id, status) {
	var url = "/user/ajax/bool/"+object+"/"+id+"/"+field+"/"+status;
	$.ajax({
		url: url,
		context: js_obj,
		success: toggle_state_success,
		error: toggle_state_fail
	});
}

$(".ajax-bool-switch").on('switchChange.bootstrapSwitch', function (event, state) {
	var fields = $(this).attr("id").split("-");
	ajax_bool($(this), fields[2], fields[3], fields[4], state);
});

$(".ajax-bool-btn").on('click', function () {
	var fields = $(this).attr("id").split("-");
	ajax_bool($(this), fields[2], fields[3], fields[4], fields[5]);
});

function toggle_state_success (data) {
	var parent = $("#"+$(this).attr("data-parent"))

	if ($(this).hasClass('require-refresh')) {
		location.reload();

	} else if ($(this).hasClass('toggle-disabled')) {
		if ($(this).prop("checked")) {
			parent.removeClass("disabled-row");
		} else {
			parent.addClass("disabled-row");
		}

	} else if ($(this).hasClass("delete-entry")) {
		parent.hide();
	}
}

function toggle_state_fail (data) {
	alert_error("Failed to save toggle state.");
}

// What the fuck shitty library? Why would you (a) not just initialize your damn
// self to the current <input value=DATE> or (b) let me do that in your initializer?
//
// Bonus bug #2: Must use the native format since the 'format' key is not
// respected during initialization.
$(".event-date-picker").each(function() {
	$(this).datetimepicker({
		inline: true,
		startDate: $(this).value,
		startTime: $(this).value,
	});
});


function item_request_new_fuzzy_success (data) {
	$("#request-fuzzy").html(data);
}

$("#request-request").on('change', function () {
	var url = "/user/ajax/item/request/new/fuzzy";
	$.post(
			url,
			{
				'new_item' : $(this).val()
			},
			item_request_new_fuzzy_success);
});

