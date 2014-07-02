
$(".date").each(function (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
});

$(".edit-item-row").on("click", "button", function () {
	btn_type = $(this).attr("id").split("-")[1];
	item_id = $(this).attr("id").split("-")[3];
	item_row = $("#item-" + item_id);

	if (btn_type == "disable") {

		// Mark the item to be disabled upon submit
		item_row.children("#item-enabled-"+item_id).val("0");

		// Gray out the item to show it will be deleted
		$("#item-" + item_id + " input:text").attr("disabled", "disabled");

		// Hide the delete button
		$(this).hide();

		// Display the undo button
		$("#btn-enable-item-" + item_id).show();

	} else if (btn_type == "enable") {

		// Mark the item as enabled
		item_row.children("#item-enabled-"+item_id).val("1");

		// Un-disable the boxes in the row
		$("#item-" + item_id + " input:text").removeAttr("disabled");

		// Hide the undo button
		$(this).hide();

		// Show the delete button again
		$("#btn-disable-item-" + item_id).show();
	}
});

$(".edit-user-row").on("click", "button", function () {
	btn_type = $(this).attr("id").split("-")[1];
	user_id = $(this).attr("id").split("-")[3];
	user_row = $("#user-" + user_id);

	if (btn_type == "disable") {

		// Mark the user to be disabled upon submit
		user_row.children("#user-enabled-"+user_id).val("0");

		// Gray out the user to show it will be deleted
		$("#user-" + user_id + " input:text").attr("disabled", "disabled");

		// Hide the delete button
		$(this).hide();

		// Display the undo button
		$("#btn-enable-user-" + user_id).show();

	} else if (btn_type == "enable") {

		// Mark the user as enabled
		user_row.children("#user-enabled-"+user_id).val("1");

		// Un-disable the boxes in the row
		$("#user-" + user_id + " input:text").removeAttr("disabled");

		// Hide the undo button
		$(this).hide();

		// Show the delete button again
		$("#btn-disable-user-" + user_id).show();
	}
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
		$("#restock-form").submit();
	}
});

