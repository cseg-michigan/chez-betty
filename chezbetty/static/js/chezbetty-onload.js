

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

$("#btn-submit-purchase").click(function () {
	purchase = {};
	purchase["umid"] = $("#user-umid").text();

	item_count = 0;
	$(".purchase-item").each(function (index) {
		id = $(this).attr("id");
		quantity = parseInt($(this).children(".item-quantity").text());
		barcode = id.split('-')[2];
		purchase[barcode] = quantity;
		item_count++;
	});

	if (item_count == 0) {
		alert_error("You must purchase at least one item.");
	} else {
		console.log(purchase);

		$.post("/purchase/new", purchase, function (data) {
			console.log(data);
		});
	}
});
