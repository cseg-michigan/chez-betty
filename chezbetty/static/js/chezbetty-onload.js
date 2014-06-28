/*
 * Chez Betty Javascript that attaches functions to event handlers.
 *
 */

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

// Click handler to submit a purchase.
$("#btn-submit-purchase").click(function () {
	console.log("submitting purchase");
	$(this).blur();
	alert_clear();

	disable_button($(this));

	// Bundle all of the product ids and quantities into an object to send
	// to the server. Also include the purchasing user.
	purchase = {};
	purchase.umid = $("#user-umid").text();

	item_count = 0;
	$(".purchase-item").each(function (index) {
		id = $(this).attr("id");
		quantity = parseInt($(this).children(".item-quantity").text());
		pid = id.split('-')[2];
		purchase[pid] = quantity;
		item_count++;
	});

	if (item_count == 0) {
		alert_error("You must purchase at least one item.");
		enable_button($(this));
	} else {
		console.log(purchase);

		// Post the order to the server
		$.ajax({
			type: "POST",
			url: "/purchase/new",
			data: purchase,
			success: purchase_success,
			error: purchase_error,
			dataType: "json"
		});
	}
});

// Click handler to submit a deposit.
$("#btn-submit-deposit").click(function () {
	$(this).blur();
	alert_clear();

	disable_button($(this));

	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.amount = strip_price($("#keypad-total").text());

	// Post the deposit to the server
	$.ajax({
		type: "POST",
		url: "/deposit/new",
		data: deposit,
		success: deposit_success,
		error: deposit_error,
		dataType: "json"
	});
});

// Button press handler for the keypad
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

$(".btn-trans-showhide").click(function () {
	var transaction_id = $(this).attr("id").split("-")[2];
	var transaction = $("#transaction-"+transaction_id)

	if (transaction.is(":visible")) {
		transaction.hide();
		$(this).text("Show");
	} else {
		transaction.show();
		$(this).text("Hide");
	}
});
