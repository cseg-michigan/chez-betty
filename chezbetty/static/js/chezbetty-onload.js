

// Click handler to remove an item from a purchase.
$("#purchase_table tbody").on("click", ".btn-remove-item", function () {
	$(this).parent().parent().slideUp().remove();

	// Check if the cart is empty and put the "Empty Order" row back in
	if ($("#purchase_table tbody tr:visible").length == 0) {
		$("#purchase-empty").show();
	}

	// Re-calculate the total
	calculate_total();
});

$("#btn-submit-purchase").click(function () {
	console.log("submitting purchase");
	$(this).blur();
	alert_clear();

	purchase = {};
	purchase.umid = $("#user-umid").text();

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
			window.location.replace("/transaction/" + data.transaction_id);
		});
	}
});

$("#keypad").on("click", "button", function () {
	var input = full_strip_price($("#keypad-total").text());
	var value = $(this).attr("id").split("-")[2];

	if (value == "del") {
		input = input.slice(0, input.length-1);
	} else {
		input += value;
	}

	var output = parseFloat(input) / 100.0;

	$("#keypad-total").text(format_price(output));
});

$("#btn-submit-deposit").click(function () {
	$(this).blur();
	alert_clear();

	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.amount = strip_price($("#keypad-total").text());

	$.post("/deposit/new", deposit, function (data) {
		window.location.replace("/transaction/" + data.transaction_id);
	});
});
