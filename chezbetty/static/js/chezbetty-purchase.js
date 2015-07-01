

// Click handler to remove an item from a purchase.
$("#purchase_table tbody").on("click", ".btn-remove-item", function () {
	$(this).parent().parent().slideUp().remove();

	// Check if the cart is empty and put the "Empty Order" row back in
	if ($("#purchase_table tbody tr:visible").length == 0) {
		$("#purchase-empty").show();

		// Make the logout button normal again
		if ($("#logout-button").attr('data-cb-href-default') !== undefined) {
			$("#logout-button").attr('href', $("#logout-button").attr("data-cb-href-default"));
		}
		$("#logout-button .btn-text-alt").hide();
		$("#logout-button .btn-text-default").show();
	}

	// Re-calculate the total
	calculate_total();
});

// Click handler to remove an item from a purchase.
$("#purchase_table tbody").on("click", ".btn-decrement-item", function () {
	quantity = parseInt($(this).parent().find("span").text()) - 1;
	$(this).parent().find("span").text(quantity);
	if (quantity < 2) {
		$(this).hide();
	}

	item_price = parseFloat($(this).parent().parent().children(".item-price-single").text());
	$(this).parent().parent().find(".item-total").html(format_price(quantity*item_price));
	calculate_total();
});

// Pass the button as "this" to this function to submit a purchase.
// We need the button so we can disable it so we don't get duplicate purchases.
function submit_purchase (this_btn, success_cb, error_cb) {
	$(this_btn).blur();
	alert_clear();

	disable_button($(this_btn));

	// Bundle all of the product ids and quantities into an object to send
	// to the server. Also include the purchasing user.
	purchase = {};
	purchase.umid = $("#user-umid").text();

	// What account to pay with?
	fields = $(this_btn).attr("id").split("-");
	if (fields.length < 3) {
		purchase["account"] = "user";
	} else {
		purchase["account"] = fields[2];
		if (purchase["account"] == "pool") {
			purchase["pool_id"] = fields["3"];
		}
	}

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
		enable_button($(this_btn));
	} else {
		// Post the order to the server
		$.ajax({
			type: "POST",
			url: "/purchase/new",
			data: purchase,
			context: this_btn,
			success: success_cb,
			error: error_cb,
			dataType: "json"
		});
	}
}

// Click handler to submit a purchase.
$(".btn-submit-purchase").click(function () {
	submit_purchase(this, purchase_success, purchase_error);
});


//
// Logout
//

// Check for items in the cart on a logout and submit the purchase
$('#logout-button').click(function () {

	if ($("#purchase-total").length) {
		// This is the purchase page
		cart_total = parseFloat(strip_price($("#purchase-total").text()));
		if (cart_total > 0) {
			// Need to pay for these items before logging out.
			submit_purchase(this, purchase_andlogout_success, purchase_error);
			return false;
		}
	}

});
