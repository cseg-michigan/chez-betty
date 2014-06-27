

// Click handler to remove an item from a purchase.
$("#purchase_table tbody").on('click', '.btn-remove-item', function () {
	$(this).parent().parent().slideUp().remove();

	// Check if the cart is empty and put the "Empty Order" row back in
	if ($("#purchase_table tbody tr:visible").length == 0) {
		$("#purchase-empty").show();
	}

	// Re-calculate the total
	calculate_total();
});

barcode = "";
$(document).keypress(function (e) {
	if (e.which == 13) {
		// Got new scan!
		console.log("barcode: " + barcode);
		add_item(barcode);
		barcode = "";
	}
	barcode += String.fromCharCode(e.which);
});
