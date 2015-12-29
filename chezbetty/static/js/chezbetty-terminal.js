/*
 * Chez Betty Main Terminal Javascript
 *
 */


/*******************************************************************************
 * GENERAL HELPER FUNCTIONS
 ******************************************************************************/


/* Functions to manipulate price strings and numbers.
 */
function format_price (price) {
	p = price.toFixed(2);

	if (p < 0) {
		return '<span class="negative">-$' + (p*-1.0).toFixed(2) + '</span>';
	} else {
		return '<span class="positive">$' + p + '</span>';
	}
}

function strip_price (price_str) {
	return price_str.replace(/^\s+|\s+$|\$/g, '');
}

function full_strip_price (price_str) {
	return price_str.replace(/^\s+|\s+$|\.|\$/g, '');
}

function clear_umid_keypad () {
	manual_umid_enter = '';
	$("#keypad-umid-status").effect("shake");
	$("#keypad-umid-status block").removeClass("umid-status-blue");
}

function deposit_alert_clear () {
	$("#deposit-alerts").empty();
}

function deposit_alert_success (error_str) {
	html = '<div class="alert alert-success" role="alert">'+error_str+'</div>';
	deposit_alert_clear();
	$("#deposit-alerts").html(html);
}

function deposit_alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	deposit_alert_clear();
	$("#deposit-alerts").html(html);
}


/*******************************************************************************
 * TERMINAL PAGE LOGIC
 ******************************************************************************/

// Function to add up the items in a cart to display the total.
function calculate_total () {
	total = 0;
	$("#purchase_table tbody tr:visible").each(function (index) {
		if ($(this).attr('id') != "purchase-empty") {
			line_total = parseFloat(
				strip_price($(this).children('.item-total').text()));
			total += line_total;
		}
	});

	var discount_td = $("#purchase-discount");
	if (typeof discount_td !== 'undefined') {
		var discount_percent_td = $("#purchase-discount-percent");
		var discount_percent_str = discount_percent_td.text().slice(1,-2);
		var discount_percent = parseFloat(discount_percent_str) * .01;
		var discount = total * discount_percent;

		$("#purchase-subtotal").html(format_price(total));

		// basic sanity check
		if ((total - discount) > 0) {
			total = total - discount;
			discount_td.html('(' + format_price(discount) + ')');
		}
	}

	$("#purchase-total").html(format_price(total));
	calculate_user_new_balance();
}

// Update the new tentative balance total for the user if the user were to
// submit the purchase and deposit.
function calculate_user_new_balance () {
	var raw_deposit = full_strip_price($("#deposit-entry-total").text());
	var deposit = parseFloat(raw_deposit) / 100.0;

	var raw_purchase = full_strip_price($("#purchase-total").text());
	var purchase = parseFloat(raw_purchase) / 100.0;

	var balance = parseFloat($("#user-balance").text());

	var new_balance = balance - purchase + deposit;
	$("#user-info-new-balance").html(format_price(new_balance));
	$("#user-info-current-balance").html(format_price(balance));
}


/*******************************************************************************
 * AJAX Callbacks
 ******************************************************************************/

// PURCHASE

// Callback when adding an item to the cart succeeds
function add_item_success (data) {
	alert_clear();

	// Check if there was an error looking up the product
	if (data.status == "disabled") {
		alert_error("That product is not currently for sale.");
	} else if (data.status == "unknown_barcode") {
		alert_error("Could not find that item.");
	} else if (data.status == "scanned_box_with_multiple_items") {
		alert_error("Cannot add that entire box to your order. Please scan an individual item.");
	} else {

		// First, if this is the first item hide the empty order row
		$("#purchase-empty").hide();
		if ($("#logout-button").attr('data-cb-href-default') === undefined) {
			$("#logout-button").attr('data-cb-href-default', $("#logout-button").attr("href"));
		}
		if ($("#logout-button").attr('data-cb-href-alt') !== undefined) {
			$("#logout-button").attr('href', $("#logout-button").attr("data-cb-href-alt"));
		}
		$("#logout-button .btn-text-alt").show();
		$("#logout-button .btn-text-default").hide();

		// Check if this item is already present. In that case we only
		// need to increment the quantity and price
		if ($("#purchase-item-" + data.id).length) {
			item_row = $("#purchase-item-" + data.id);

			// Increment the quantity
			quantity = parseInt(item_row.find(".item-quantity span").text()) + 1;
			item_price = parseFloat(item_row.children(".item-price-single").text());

			item_row.find(".item-quantity span").text(quantity);
			item_row.children(".item-total").html(format_price(quantity*item_price));

			if (quantity >= 2) {
				item_row.find("td .btn-decrement-item").show();
			}

		} else {
			// Add a new item
			$("#purchase_table tbody").append(data.item_row_html);
		}

		calculate_total();

	}
}

// Callback when adding to cart fails.
function add_item_fail () {
	alert_error("Could not find that item.");
}

// Callback when a purchase was successful
function purchase_success (data) {
	if ("error" in data) {
		alert_error(data.error);
		enable_button($(".btn-submit-purchase"));
	} else if ("redirect_url" in data) {
		window.location.replace(data.redirect_url);
	} else {
		// On successful purchase, redirect the user to the transaction complete
		// page showing the transaction.
		window.location.replace("/terminal/event/" + data.event_id);
	}
}

// Callback when a purchase was successful and we want to log the user out
// afterwards.
function purchase_andlogout_success (data) {
	if ("error" in data) {
		alert_error(data
			.error);
		enable_button($(".btn-submit-purchase"));
	} else {
		// Follow the link from the button's href
		window.location.replace($(this).attr('href'));
	}
}

// Callback when a purchase fails for some reason
function purchase_error () {
	alert_error("Failed to complete purchase. Perhaps try again?");
	enable_button($(".btn-submit-purchase"));
}

// DEPOSIT

// Callback when a deposit POST was successful
function deposit_success (data) {
	if ("error" in data) {
		deposit_alert_error(data.error);
		enable_button($(".btn-submit-deposit"));
		enable_button($(".btn-delete-deposit"));
	} else {
		// On successful deposit, we switch to the frame that shows
		// the successful deposit.

		// Setup the page with amount/event/pool
		$(".deposit-amount").html(format_price(data.amount));
		if (data.pool_name) {
			$(".deposit-pool-name").text(data.pool_name);
			$("#deposit-complete-user").hide();
			$("#deposit-complete-pool").show();
		} else {
			$("#deposit-complete-pool").hide();
			$("#deposit-complete-user").show();
		}

		// Update user balance
		$("#user-balance").text(data.user_balance);
		calculate_user_new_balance();

		$("#deposit-eventid").text(data.event_id);
		$("#deposit-amount").text(data.amount);

		// Make the change
		$("#deposit-entry").hide();
		$("#deposit-complete").show();

		// Also enable these buttons so they don't get stuck
		enable_button($(".btn-submit-deposit"));
		enable_button($(".btn-delete-deposit"));
	}
}

// Callback when a deposit fails for some reason
function deposit_error () {
	deposit_alert_error("Failed to complete deposit. Perhaps try again?");
	enable_button($(".btn-submit-deposit"));
	enable_button($(".btn-delete-deposit"));
	$("#deposit-entry-total").html(format_price(0.0));
}

// Callback when a deposit delete POST was successful
function deposit_delete_success (data) {
	if ("error" in data) {
		deposit_alert_error(data.error);
		enable_button($(".btn-submit-deposit"));
		enable_button($(".btn-delete-deposit"));
	} else {
		// Clear some state
		$("#deposit-eventid").text();
		$("#deposit-amount").text();

		deposit_alert_success('Deposit successfully removed.');

		// Update user balance
		$("#user-balance").text(data.user_balance);
		calculate_user_new_balance();

		// Make the change back to the deposit entry form
		$("#deposit-complete").hide();
		$("#deposit-entry").show();

		// Also enable these buttons so they don't get stuck
		enable_button($(".btn-submit-deposit"));
		enable_button($(".btn-delete-deposit"));
	}
}

// Callback when a deposit delete fails for some reason
function deposit_delete_error () {
	deposit_alert_error("Failed to delete deposit. Perhaps try again?");
	enable_button($(".btn-submit-deposit"));
	enable_button($(".btn-delete-deposit"));
}


/*******************************************************************************
 * EVENT HANDLERS
 ******************************************************************************/

// DEPOSIT

// Click handler to submit a deposit.
$(".btn-submit-deposit").click(function () {
	$(this).blur();
	deposit_alert_clear();

	disable_button($(this));

	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.amount = strip_price($("#deposit-entry-total").text());

	// Clear deposit keypad box
	$("#deposit-entry-total").html(format_price(0.0));

	// What account to deposit to?
	fields = $(this).attr("id").split("-");
	deposit.account = fields[2];
	if (deposit.account == "pool") {
		deposit.pool_id = fields["3"];
	}

	// Post the deposit to the server
	$.ajax({
		type:     "POST",
		url:      "/terminal/deposit",
		data:     deposit,
		success:  deposit_success,
		error:    deposit_error,
		dataType: "json"
	});
});

// Click handler to submit a deposit.
$(".btn-delete-deposit").click(function () {
	$(this).blur();
	deposit_alert_clear();

	disable_button($(this));

	// Fill in the keypad box
	var prev_amount = parseFloat($("#deposit-amount").text());
	$("#deposit-entry-total").html(format_price(prev_amount));

	// Prepare enough information so we can delete the old
	// deposit transaction
	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.old_event_id = $("#deposit-eventid").text();

	// Post the deposit to the server
	$.ajax({
		type:     "POST",
		url:      "/terminal/deposit/delete",
		data:     deposit,
		success:  deposit_delete_success,
		error:    deposit_delete_error,
		dataType: "json"
	});
});

// Button press handler for the default deposit amount buttons
$(".btn-default-deposit").click(function() {
	var value = $(this).attr("id").split("-")[2];
	$("#deposit-entry-total").html(format_price(parseFloat(value)));
	calculate_user_new_balance();
});

// Switch to custom amount entry mode
$("#btn-deposit-entry-default-custom").click(function() {
	$("#deposit-entry-default").hide();
	$("#deposit-entry-custom").show();
	$("#deposit-entry-total").html(format_price(0.0));
});

// Switch to standard amount deposits from the custom page
$("#btn-deposit-entry-custom-default").click(function() {
	$("#deposit-entry-custom").hide();
	$("#deposit-entry-default").show();
	$("#deposit-entry-total").html(format_price(0.0));
});

// Button press handler for the keypad
$("#deposit-entry-custom").on("click", "button", function () {
	var input = full_strip_price($("#deposit-entry-total").text());
	var value = $(this).attr("id").split("-")[2];

	if (value == "del") {
		input = input.slice(0, input.length-1);
	} else if (value == "clr") {
		input = 0;
	} else {
		input += value;
	}

	var output = parseFloat(input) / 100.0;

	$("#deposit-entry-total").html(format_price(output));
	calculate_user_new_balance();
});


// PURCHASE

// Function called by chezbetty-item.js when a new item was scanned and
// should be added to the cart.
function add_item (item_id) {
	$.ajax({
		dataType: "json",
		url: "/terminal/purchase/item/"+item_id+"/json",
		success: add_item_success,
		error: add_item_fail
	});
}

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
			url: "/terminal/purchase/new",
			data: purchase,
			context: this_btn,
			success: success_cb,
			error: error_cb,
			dataType: "json"
		});
	}
}

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

// Click handler to submit a purchase.
$(".btn-submit-purchase").click(function () {
	submit_purchase(this, purchase_success, purchase_error);
});



// TERMINAL INDEX PAGE

var manual_umid_enter = '';
var manual_umid_timeout = -1;
// Button press handler for the umid keypad
$("#keypad-umid").on("click", "button", function () {

	if (manual_umid_enter.length < 8) {
		// If we haven't gotten enough of a UMID yet then we are cool
		// to keep taking inputs

		var value = $(this).attr("id").split("-")[2];
		if (value == 'del') {
			var num = manual_umid_enter.length;
			if (num == 0) {
				return;
			}
			$("#keypad-umid-status block:eq("+(8-num)+")").removeClass("umid-status-blue");
			manual_umid_enter = manual_umid_enter.slice(0, -1);
		} else if (value == 'clear') {
			clear_umid_keypad();
		} else {
			manual_umid_enter += value;

			var num = manual_umid_enter.length;
			$("#keypad-umid-status block:eq("+(8-num)+")").addClass("umid-status-blue");
		}

		if (manual_umid_enter.length == 8) {
			$.ajax({
				type: "POST",
				url: "/terminal/check",
				data: {'umid': manual_umid_enter},
				success: function (data) {
					if (data.status == 'success') {
						window.location = '/terminal/' + manual_umid_enter;
					} else {
						alert_error(data.msg);
						clear_umid_keypad();
					}
				},
				error: function (data) {
					if (manual_umid_timeout >= 0) {
						clearTimeout(manual_umid_timeout);
					}
					clear_umid_keypad();
				},
				dataType: "json"
			});

		} else {
			if (manual_umid_timeout >= 0) {
				clearTimeout(manual_umid_timeout);
			}
			if (manual_umid_enter.length) {
				// Want to clear things if someone gets halfway through and quits.
				// Wait 15 seconds.
				manual_umid_timeout = setTimeout(clear_umid_keypad, 15000);
			}
		}
	}
});

