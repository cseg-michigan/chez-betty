

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

//$("#btn-items-add-row")