
$(".date").each(function (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
});

// Make the Demo Mode checkbox in the sidebar a pretty on/off slider
$("[name='admin-demo-mode']").bootstrapSwitch();
$('input[name="admin-demo-mode"]').on('switchChange.bootstrapSwitch', function (event, state) {
	$.ajax({
		dataType: "json",
		url: "/admin/demo/" + state,
		success: demo_state_success,
		error: demo_state_fail
	});
	console.log('called ajax with state ' + state);
});

function demo_state_success (data) {
	console.log('demo state updated');
}

function demo_state_fail (data) {
	console.log('demo state update failed');
	// Reset the checkbox to indicate the failure
	var cb = $('input[name="admin-demo-mode"]');
	cb.bootstrapSwitch('toggleState', skip=true);
	alert_error("Failed to save demo state.");
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

$(".edit-user-row").on("click", "button", function () {
	toggle_enabled("user", $(this));
});

$(".edit-vendor-row").on("click", "button", function () {
	toggle_enabled("vendor", $(this));
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
});

$("#restock-table").on("input", "input:text",  function () {
	calculate_total();
});

$("#restock-table").on("click", "input:checkbox", function () {
	calculate_total();
});

// Check that sales tax matches up
$("#restock-button").click(function () {
	var user_sales_tax = parseFloat(strip_price($("#restock-salestax").val()));
	if (isNaN(user_sales_tax)) {
		user_sales_tax = 0.0;
	}

	var calc_sales_tax = 0.0;
	$(".restock-item").each(function (index) {
		var id = $(this).attr("id").split("-")[2];
		if ($("#restock-salestax-"+id+":checked").length > 0) {
			var price = calculate_price($("#restock-cost-"+id).val());
			calc_sales_tax += 0.06*price;
		}
	});

	if (Math.abs(user_sales_tax - calc_sales_tax) >= 0.01) {
		// Sales tax calculation is wrong. Something isn't rigth here.
		alert_error("Sales tax calculation invalid. Did you forget something that was taxed?");
	} else {
		clicked_submit = true;
		$("#restock-form").submit();
	}
});



//
// Check for unsaved data in forms
//
var serialized_form_clean;
var clicked_submit = false;

// When the page load we get the values serialize
serialized_form_clean = $("form").serialize(); 

// Before we leave the page we now compare between the new form values and the orignal
window.onbeforeunload = function (e) {
    var serialized_form_dirty = $("form").serialize();
    if (serialized_form_clean != serialized_form_dirty && !clicked_submit) {
        return "You are about to leave a page where you have not saved the data.";
    }
};

$("button:submit").click(function () {
	clicked_submit = true;
});

