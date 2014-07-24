
$(".date").each(function (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
});

// Make the Demo Mode checkbox in the sidebar a pretty on/off slider
$(".admin-switch").bootstrapSwitch();
$(".admin-switch").on('switchChange.bootstrapSwitch', function (event, state) {
	var type = $(this).attr("id").split("-")[1];
	$.ajax({
		url: "/admin/" + type + "/" + state,
		success: toggle_state_success,
		error: toggle_state_fail
	});
});

function toggle_state_success (data) {
}

function toggle_state_fail (data) {
	alert_error("Failed to save toggle state.");
}

function toggle_enabled (type, btn) {
	btn_type = btn.attr("id").split("-")[1];
	id = btn.attr("id").split("-")[3];
	row = $("#"+type+"-" + id)

	if (btn_type == "disable") {

		// Mark the row to be disabled upon submit
		row.children("#"+type+"-enabled-"+id).val("0");

		// Gray out the row to show it will be deleted
		$("#"+type+"-" + id + " input:text").attr("disabled", "disabled");

		// Hide the delete button
		btn.hide();

		// Display the undo button
		$("#btn-enable-"+type+"-" + id).show();

	} else if (btn_type == "enable") {

		// Mark the user as enabled
		row.children("#"+type+"-enabled-"+id).val("1");

		// Un-disable the boxes in the row
		$("#"+type+"-" + id + " input:text").removeAttr("disabled");

		// Hide the undo button
		btn.hide();

		// Show the delete button again
		$("#btn-disable-"+type+"-" + id).show();
	}
}

$(".edit-item-row").on("click", "button", function () {
	toggle_enabled("item", $(this));
});

$(".edit-box-row").on("click", "button", function () {
	toggle_enabled("box", $(this));
});

$(".edit-user-row").on("click", "button", function () {
	toggle_enabled("user", $(this));
});

$(".edit-vendor-row").on("click", "button", function () {
	toggle_enabled("vendor", $(this));
});

$(".edit-announcement-row").on("click", "button", function () {
	toggle_enabled("announcement", $(this));
});

// Add a new row to the add items form
$("#btn-items-add-row").click(function () {

	// Instead of counting each time, just keep the number of lines around
	// in a hidden element.
	var item_lines_count = parseInt($("#new-items-number").val());

	// Copy row 0 to create a new row
	container = $("#new-item-0").clone().attr("id", "new-item-"+item_lines_count);
	container.find("input").each(function (index) {
		// Update the ID to the next number
		id = $(this).attr("id");
		name_pieces = id.split("-");
		name_pieces[name_pieces.length-1] = item_lines_count;
		new_id = name_pieces.join("-");
		$(this).attr("id", new_id);
		$(this).attr("name", new_id);
		if ($(this).is(":checkbox")) {
			// Reset the checkmark so new products are enabled by default
			$(this).prop("checked", "checked");
		} else {
			// Clear the value if there is text in the first row already
			$(this).val("");
		}
	});

	// Add the new row to the page
	$("#new-items").append(container);

	// Update the number of new items to be added
	$("#new-items-number").val(item_lines_count+1);

	attach_keypad();
});

$("#select-user").change(function () {
	user_id = $("#select-user option:selected").val();
	console.log(user_id);

	// Hide all current balances
	$(".current-balance").hide();

	// Show the correct current balance for this user
	$("#current-balance-"+user_id).show();

	update_new_balance();
});

$("#balance-change-amount").on("input", function () {
	update_new_balance();
});

$("#edit-items").click(function () {
	alert_clear();
});

// Update markup
$("#edit-items").on("input", "input:text",  function () {
	var id = $(this).attr("id").split("-")[2];
	var price = parseFloat($("#item-price-"+id).val());
	var wholesale = parseFloat($("#item-wholesale-"+id).val());

	var markup = (((price/wholesale) - 1.0) * 100.0).toFixed(2);
	$("#item-markup-"+id).text(markup + "%");
	$("#item-markup-"+id).attr("data-value", markup);
});

$(".restock-manual").on("click", function () {
	var type = $(this).attr("id").split("-")[2];
	add_item($("#restock-manual-"+type+"-select").val());
});

$("#restock-table").on("click", "input:checkbox", function () {
	restock_update_line_total($(this).attr("id").split("-")[2]);
});

// When the per item cost changes, update the line item total
$("#restock-table").on("input", "input:text", function () {
	restock_update_line_total($(this).attr("id").split("-")[2]);
});


$(".request-delete").click(function () {
	var request_id = $(this).attr("id").split("-")[3];

	$.ajax({
		url: "/admin/request/delete/" + request_id,
		success: request_delete_success,
		error: request_delete_fail
	});
})



//
// Check for unsaved data in forms
//
var serialized_form_clean;
var clicked_submit = false;

// When the page load we get the values serialize
serialized_form_clean = $("form").serialize().split("&").sort().join("&");

// Before we leave the page we now compare between the new form values and the orignal
window.onbeforeunload = function (e) {
	console.log(serialized_form_clean);
    var serialized_form_dirty = $("form").serialize().split("&").sort().join("&");
    if (serialized_form_clean != serialized_form_dirty && !clicked_submit) {
        return "You are about to leave a page where you have not saved the data.";
    }
};

$("button:submit").click(function () {
	clicked_submit = true;
});

