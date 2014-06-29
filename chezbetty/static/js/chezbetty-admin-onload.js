

$(".edit-item-row").on("click", "button", function () {
	btn_type = $(this).attr("id").split("-")[1];
	item_id = $(this).attr("id").split("-")[3];
	item_row = $("#item-" + item_id);

	if (btn_type == "delete") {

		// Mark the item to be delete upon submit
		item_row.addClass("to-delete");

		// Gray out the item to show it will be deleted
		item_row.children("div").each(function () {
			if (!$(this).hasClass("item-actions")) {
				overlay = $('<div>', {
					css: {
						position: 'absolute',
						width: $(this).outerWidth(),
						height: $(this).outerHeight(),
						top: $(this).position().top,
						left: $(this).position().left,
						backgroundColor: 'rgba(255,255,255,0.5)',
						zIndex: 10},
					class: "item-gray-out"
				}).appendTo(item_row);
			}
		});


		// Hide the delete button
		$(this).hide();

		// Display the undo button
		$("#btn-undelete-item-" + item_id).show();

	} else if (btn_type == "undelete") {

		// Remove the delete mark
		item_row.removeClass("to-delete");

		// Remove the gray overlays
		item_row.children(".item-gray-out").remove();

		// Hide the undo button
		$(this).hide();

		// Show the delete button again
		$("#btn-delete-item-" + item_id).show();
	}
});