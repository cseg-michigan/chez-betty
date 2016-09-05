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

function purchase_alert_clear () {
	$("#purchase-alerts").empty();
}

function purchase_alert_success (error_str) {
	html = '<div class="alert alert-success" role="alert">'+error_str+'</div>';
	purchase_alert_clear();
	$("#purchase-alerts").html(html);
}

function purchase_alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	purchase_alert_clear();
	$("#purchase-alerts").html(html);
}


/*******************************************************************************
 * TERMINAL PAGE LOGIC
 ******************************************************************************/

// Returns the current balance of the user that is logged in on terminal
function get_user_balance () {
	return parseFloat($("#user-balance").text());
}

function get_pool_balance (pool_id) {
	return parseFloat($("#pool-balance-"+pool_id).text());
}

// Function to add up the items in a cart to display the total.
function calculate_total () {
	total = 0;
	$("#purchase-table tr.purchase-item").each(function (index) {
		if ($(this).attr('id') != "purchase-empty") {
			line_total = parseFloat(
				strip_price($(this).children('.item-total').text()));
			total += line_total;
		}
	});

	var balance = get_user_balance();
	var discount = 0.0;
	var fee = 0.0;
	var need_subtotal = false;

	// Set Subtotal row
	$("#purchase-subtotal").html(format_price(total));

	// Hide or show discount / fee rows
	if (balance > 20.0) {
		// Good standing discount!
		var discount_percent_td = $("#purchase-discount-percent");
		var discount_percent_str = discount_percent_td.text().slice(1,-2);
		var discount_percent = parseFloat(discount_percent_str) * 0.01;
		var discount = Math.round((total * discount_percent) * 100) / 100;

		// Make sure nothing looks strange
		if (discount > total) discount = 0.0;

		// Set discount row
		$("#purchase-discount").html('(' + format_price(discount) + ')');
		$("#purchase-row-goodstanding").show();
		need_subtotal = true;
	} else {
		$("#purchase-row-goodstanding").hide();
	}

	if ((balance - total - discount) <= -5.0) {
		// Wall of shame fee!
		var fee_percent = calculate_wallofshame_fee_percent(balance, total-discount);
		var fee = Math.round(((total-discount) * (fee_percent * 0.01)) * 100) / 100;

		// Setup fee row
		$("#purchase-fee-percent-amount").html(fee_percent.toFixed(1));
		$("#purchase-fee").html(format_price(fee));
		$("#purchase-row-wallshame").show();
		need_subtotal = true;
	} else {
		$("#purchase-row-wallshame").hide();
	}

	// Show or hide subtotal row
	if (need_subtotal) {
		$("#purchase-row-subtotal").show();
	} else {
		$("#purchase-row-subtotal").hide();
	}

	// Calculate the total after any discount or fee
	var new_total = total - discount + fee;

	$("#purchase-total").html(format_price(new_total));
	calculate_user_new_balance();
}

// Update the stored user balance in the DOM if it changes. Also
// update any GUI elements that are based on that balance.
function update_user_balance (balance) {
	// Set the DOM element
	$("#user-balance").text(balance);

	// Show/hide the top announcements
	$(".user-alert-balance").hide();
	if (balance < -50) {
		$("#user-alert-balance-large").show();
	} else if (balance < -20) {
		$("#user-alert-balance-medium").show();
	}

	// Update the all places where current balance might be displayed
	$(".current-formatted-balance").html(format_price(parseFloat(balance)));

	// Update the color formatting based on amount in account
	if (balance < -5) $("#user-info-current-balance").addClass("big-debt");
	else $("#user-info-current-balance").removeClass("big-debt");
}

// Returns the pool id if a pool payment is selected, otherwise returns -1
// if the user account is paying.
function get_active_payment_account () {
	var account_button = $(".purchase-payment.active");
	var id = account_button.attr('id');
	var fields = id.split('-');
	var acct_type = fields[1];
	if (acct_type == 'pool') {
		return parseInt(fields[2]);
	}
	return -1;
}

function display_and_update_pool_balance_box () {
	var active_account = get_active_payment_account();

	if (active_account == -1) {
		// Hide the pool balance box
		$('#pool-info-current-balance').hide();
	} else {
		// Get the pool balance
		var balance = get_pool_balance(active_account);
		$("#pool-info-current-balance span").html(format_price(balance));
		$('#pool-info-current-balance').show();
	}
}

// Update the new tentative balance total for the user if the user were to
// submit the purchase and deposit.
function calculate_user_new_balance () {
	var raw_deposit = full_strip_price($("#deposit-entry-total").text());
	var deposit = parseFloat(raw_deposit) / 100.0;

	// Clear deposit amount if we are on deposit complete
	if ($("#deposit-complete:visible").length == 1) {
		deposit = 0.00;
	}

	var raw_purchase = full_strip_price($("#purchase-total").text());
	var purchase = parseFloat(raw_purchase) / 100.0;

	// Clear purchase amount if we are on purchase complete
	if ($("#purchase-complete:visible").length == 1) {
		purchase = 0.00;
	}

	var balance = get_user_balance();

	// Only do this calculation if we are not using a pool
	if (get_active_payment_account() == -1) {
		var new_balance = balance - purchase + deposit;
	} else {
		var new_balance = balance;
	}
	$("#user-info-new-balance span").html(format_price(new_balance));

	// Update the color formatting based on amount in account
	if (new_balance < -5) $("#user-info-new-balance").addClass("big-debt");
	else $("#user-info-new-balance").removeClass("big-debt");
}

// Display and hide logout buttons based on user balance
function show_correct_purchase_button () {
	if ($("#purchase-complete:visible").length == 1) {
		// If we are on the purchase complete page, show logout
		$("#purchase-button-purchaselogout").hide();
		$("#purchase-button-purchase").hide();
		$("#purchase-button-logout").show();

	} else if ($("#purchase-empty:visible").length == 1) {
		// If there is nothing in the cart, then it should be a logout button
		$("#purchase-button-purchaselogout").hide();
		$("#purchase-button-purchase").hide();
		$("#purchase-button-logout").show();
	} else {
		$("#purchase-button-logout").hide();

		// If the user is in debt, it should be just a purchase button
		var balance = parseFloat($("#user-balance").text());
		if (balance < 0 && get_active_payment_account() == -1) {
			// If the user is paying with pool, then we can have purchase and
			// logout button.
			$("#purchase-button-purchaselogout").hide();
			$("#purchase-button-purchase").show();
		} else {
			$("#purchase-button-purchaselogout").show();
			$("#purchase-button-purchase").hide();
		}
	}
}

function calculate_wallofshame_fee_percent (balance, total) {
	// If not on wall of shame, nor going to be, no fee
	if (balance - total > -5.0) return 0.0;

	// Calculate the correct fee.
	// Need to get the amount we will charge the fee on
	var remainder = (balance - total) * -1;
	var offset = balance * -1;
	if (balance > -5) {
		offset = 5;
	}
	var fee_percent = Math.floor(offset / 5.0) * 5;
	var fee = 0;

	// This works only because we increase the fee every $5 dollars
	// and we increase the fee in 5% increments.
	while (true) {
		var extra = remainder - offset;

		if (remainder < fee_percent + 5) {
			fee += ((fee_percent * 0.01) * extra);
			break;

		} else {
			fee += ((fee_percent * 0.01) * (fee_percent + 5 - offset));
			fee_percent += 5;
			offset = fee_percent;
		}
	}

	if (total > 0) {
		fee_percent = (fee / total) * 100;
	}

	if (fee_percent < 0.1) {
		fee_percent = 0.1;
	}

	return fee_percent;
}

// Returns true if a user has logged in to purchase something
function logged_in () {
	var umid = $("#user-umid").text();
	if (umid === '') return false;
	return true;
}

/*******************************************************************************
 * AJAX Callbacks
 ******************************************************************************/

// PURCHASE

// Callback when adding an item to the cart succeeds
function add_item_success (data) {
	purchase_alert_clear();

	if ("error" in data) {
		purchase_alert_error(data.error);
	} else {
		// First, if this is the first item hide the empty order row
		$("#purchase-empty").hide();

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
			$("#purchase-table tbody").append(data.item_row_html);
		}

		// Want to make sure the correct logout button is displayed
		show_correct_purchase_button();

		calculate_total();
	}
}

// Callback when adding to cart fails.
function add_item_fail () {
	purchase_alert_error("Could not find that item.");
}

// Callback when saving an item for when a user logs in succeeds
function save_item_success (data) {
	purchase_alert_clear();

	if ("error" in data) {
		alert_error('Could not add that item right now.');
	} else {
		alert_success('Item successfully scanned. Log in to add it to your cart.')
	}
}

// Callback when adding to cart fails.
function save_item_fail () {
	alert_error('Could not add that item right now.');
}

// Callback when a purchase was successful
function purchase_success (data) {
	if ("error" in data) {
		purchase_alert_error(data.error);
	} else {
		purchase_alert_success('Purchase was recorded successfully.');

		// Throw in table summarizing
		$("#purchase-complete-table").html(data.order_table);

		// Flip to complete page
		$("#purchase-entry").hide();
		$("#purchase-complete").show();

		// Update buttons
		show_correct_purchase_button();

		// Update user balance
		update_user_balance(data.user_balance);
		calculate_user_new_balance();
	}

	enable_button($(".btn-submit-purchase"));
}

// Callback when a purchase was successful and we want to log the user out
// afterwards.
function purchase_andlogout_success (data) {
	if ("error" in data) {
		purchase_alert_error(data.error);
		enable_button($(".btn-submit-purchase"));
	} else {
		// Follow the link from the button's href
		window.location.replace('/');
	}
}

// Callback when a purchase fails for some reason
function purchase_error () {
	purchase_alert_error("Failed to complete purchase. Perhaps try again?");
	enable_button($(".btn-submit-purchase"));
}

// Callback when a purchase delete POST was successful
function purchase_delete_success (data) {
	if ("error" in data) {
		purchase_alert_error(data.error);
		enable_button($(".btn-delete-purchase"));
	} else {
		// Clear some state
		$("#purchase-complete-table").html('');

		purchase_alert_success('Purchase successfully removed.');

		// Flip back to cart contents page
		$("#purchase-complete").hide();
		$("#purchase-entry").show();

		// Update buttons
		show_correct_purchase_button();

		// Update user balance
		update_user_balance(data.user_balance);
		calculate_user_new_balance();

		// Also enable these buttons so they don't get stuck
		enable_button($(".btn-submit-purchase"));
	}
}

// Callback when a deposit purchase fails for some reason
function purchase_delete_error () {
	purchase_alert_error("Failed to delete purchase. Perhaps try again?");
	enable_button($(".btn-delete-purchase"));
}

// Callback when we get a list of items for a tag
function purchase_tag_success (data) {
	if ('error' in data) {
		//not sure
	} else {
		$('#tag-items-content').html(data.items_html);
		$('#tags').hide();
		$('#tag-items').show();
	}
}

// Callback when getting an item list fails
function purchase_tag_error () {

}

// DEPOSIT

// Callback when a deposit POST was successful
function deposit_success (data) {
	if (logged_in()) {
		deposit_alert_clear();
		enable_button($('.btn-submit-purchase'));

		if ("error" in data) {
			deposit_alert_error(data.error);
			enable_button($("#btn-confirm-deposit-yes"));

			$("#deposit-main").hide();
			$("#deposit-verify").hide();
			$("#deposit-counting").hide();
			$("#deposit-complete").hide();
			$("#deposit-coins").show();
		} else {
			// On successful deposit, we switch to the frame that shows
			// the successful deposit.

			// Setup the page with amount/event
			$(".deposit-amount").html(format_price(data.amount));
			$("#deposit-complete-user").show();

			// Update user balance
			update_user_balance(data.user_balance);

			// We then calculate the purchase total in case a discount/fee
			// has changed.
			calculate_total();

			$("#deposit-eventid").text(data.event_id);
			$("#deposit-amount").text(data.amount);

			// Make the change
			$("#deposit-main").hide();
			$("#deposit-coins").hide();
			$("#deposit-verify").hide();
			$("#deposit-counting").hide();
			$("#deposit-complete").show();
		}
	} else {
		var alert_str = 'Deposit of '+format_price(data.new_amount)+' recorded.'
		alert_str += ' Please log in to add '+format_price(data.total_amount)+' to your account.'
		alert_success(alert_str);
	}
}

// Callback when a deposit fails for some reason
function deposit_error () {
	if (logged_in()) {
		deposit_alert_error("Failed to complete deposit. Email chezbetty@umich.edu and let them know.");
		enable_button($(".btn-confirm-deposit-yes"));
		enable_button($('.btn-submit-purchase'));
		$("#deposit-counting").hide();
		$("#deposit-entry-total").html(format_price(0.0));
	} else {
		alert_error("Failed to complete deposit. Email chezbetty@umich.edu and let them know.");
	}
}


/*******************************************************************************
 * EVENT HANDLERS
 ******************************************************************************/

// PURCHASE

// Function called by chezbetty-item.js when a new item was scanned and
// should be added to the cart.
function add_item (barcode) {
	if (logged_in()) {
		// Request information about the product so we can add it to the cart
		$.ajax({
			dataType: "json",
			url: "/terminal/item/barcode/"+barcode,
			success: add_item_success,
			error: add_item_fail
		});
	} else {
		// Save this item for when the user does log in
		$.ajax({
			dataType: "json",
			url: "/terminal/saveitem/barcode/"+barcode,
			success: save_item_success,
			error: save_item_fail
		});
	}
}

function add_item_id (item_id) {
	$.ajax({
		dataType: "json",
		url: "/terminal/item/id/"+item_id,
		success: add_item_success,
		error: add_item_fail
	});
}

// Pass the button as "this" to this function to submit a purchase.
// We need the button so we can disable it so we don't get duplicate purchases.
function submit_purchase (this_btn, success_cb, error_cb) {
	$(this_btn).blur();
	purchase_alert_clear();

	disable_button($(this_btn));

	// Bundle all of the product ids and quantities into an object to send
	// to the server. Also include the purchasing user.
	purchase = {};
	purchase.umid = $("#user-umid").text();

	// What account to pay with?
	var pool_id = get_active_payment_account();
	if (pool_id > -1) {
		purchase['pool_id'] = pool_id;
	}

	var item_count = 0;
	$(".purchase-item").each(function (index) {
		var id = $(this).attr("id");
		var quantity = parseInt($(this).children(".item-quantity").text());
		var pid = id.split('-')[2];
		if (pid in purchase) {
			purchase[pid] += quantity;
		} else {
			purchase[pid] = quantity;
		}
		item_count++;
	});

	if (item_count == 0) {
		// This should never happen as the purchase button should not be visible
		purchase_alert_error("You must purchase at least one item.");
		enable_button($(this_btn));
	} else {
		// Post the order to the server
		$.ajax({
			type:     "POST",
			url:      "/terminal/purchase",
			data:     purchase,
			context:  this_btn,
			success:  success_cb,
			error:    error_cb,
			dataType: "json"
		});
	}
}

// Click handler to remove an item from a purchase.
$("#purchase-table tbody").on("click", ".btn-remove-item", function () {
	$(this).parent().parent().slideUp().remove();

	// Check if the cart is empty and put the "Empty Order" row back in
	if ($("#purchase-table tbody tr:visible").length == 0) {
		$("#purchase-empty").show();

		// Make the logout button normal again
		show_correct_purchase_button();
	}

	// Re-calculate the total
	calculate_total();
});

// Click handler to remove an item from a purchase.
$("#purchase-table tbody").on("click", ".btn-decrement-item", function () {
	// Make sure scanning doesn't push this button
	this.blur();

	var quantity_span = $(this).parent().parent().find(".item-quantity span");
	var quantity = parseInt(quantity_span.text()) - 1;
	quantity_span.text(quantity);
	if (quantity < 2) {
		$(this).hide();
	}

	var item_price = parseFloat($(this).parent().parent().children(".item-price-single").text());
	$(this).parent().parent().find(".item-total").html(format_price(quantity*item_price));
	calculate_total();
});

// Increase the number of a given item in the cart
$("#purchase-table tbody").on("click", ".btn-increment-item", function () {
	// Make sure scanning doesn't push this button
	this.blur();

	var quantity_span = $(this).parent().parent().find(".item-quantity span");
	var quantity = parseInt(quantity_span.text()) + 1;
	quantity_span.text(quantity);

	if (quantity >= 2) {
		$(this).parent().parent().find(".btn-decrement-item").show();
	}

	var item_price = parseFloat($(this).parent().parent().children(".item-price-single").text());
	$(this).parent().parent().find(".item-total").html(format_price(quantity*item_price));
	calculate_total();
});

// Choose which account to pay from
$(".purchase-payment").click(function () {
	$(".purchase-payment").removeClass("active");
	$(this).addClass("active");

	// Update boxes on the left showing current balance and new balance
	calculate_user_new_balance();

	// Show or hide pool balance
	display_and_update_pool_balance_box();

	// Can also switch payment options
	show_correct_purchase_button();
});

// Purchase mistake, revert this transaction and put the cart back
$("#purchase-complete-table").on("click", ".btn-delete-purchase", function () {
	$(this).blur();
	purchase_alert_clear();

	disable_button($(this));

	var event_id = parseInt($(this).attr('id').split('-')[2]);

	// Prepare enough information so we can delete the old
	// deposit transaction
	purchase = {};
	purchase.umid = $("#user-umid").text();
	purchase.old_event_id = event_id;

	// Post the deposit to the server
	$.ajax({
		type:     "POST",
		url:      "/terminal/purchase/delete",
		data:     purchase,
		success:  purchase_delete_success,
		error:    purchase_delete_error,
		dataType: "json"
	});
});

// Nothing in the cart, just logout
$("#purchase-button-logout").click(function () {
	window.location.href = "/";
});

// Click handler to submit a purchase and logout.
$("#purchase-button-purchaselogout").click(function () {
	submit_purchase(this, purchase_andlogout_success, purchase_error);
});

// Click handler to submit a purchase.
$("#purchase-button-purchase").click(function () {
	submit_purchase(this, purchase_success, purchase_error);
});

// Clicked to choose an item on the terminal
$('#btn-nobarcode').click(function () {
	$('#panel-purchase').hide();
	$('#panel-nobarcode').show();
});

// Go back to purchase cart
$('#btn-nobarcode-tags-back').click(function () {
	$('#panel-nobarcode').hide();
	$('#panel-purchase').show();
});

// Go back to purchase cart
$('#btn-nobarcode-tag-items-back').click(function () {
	$('#tag-items').hide();
	$('#tags').show();
});

// Choose a tag to view items
$('.btn-nobarcode-tag').click(function () {
	var tag_id = $(this).attr('data-tagid');

	$.ajax({
		type:     "GET",
		url:      "/terminal/purchase/tag/" + tag_id,
		success:  purchase_tag_success,
		error:    purchase_tag_error,
	});
});

$('#tag-items').on('click', '.tag-item', function () {
	var item_id = $(this).attr('data-item-id');

	add_item_id(item_id);

	$('#tag-items').hide();
	$('#panel-nobarcode').hide();
	$('#tags').show();
	$('#panel-purchase').show();
});

$('#recently-purchased').on('click', '.tag-item', function () {
	console.log($(this));
	var item_id = $(this).attr('data-item-id');
	add_item_id(item_id);
});

// DEPOSIT

// Called to let the user know we got the bill, we just need time to count it.
function start_deposit () {
	disable_button($('.btn-submit-purchase'));
	$("#deposit-counting").show();
}

function handle_deposit (amount, method) {
	deposit = {};

	// If this is empty, then the user is not logged in. That's ok,
	// we save the deposit for the next user
	deposit.umid = $("#user-umid").text();
	deposit.amount = amount;
	deposit.method = method;

	// Post the deposit to the server
	$.ajax({
		type:     "POST",
		url:      "/terminal/deposit",
		data:     deposit,
		success:  deposit_success,
		error:    deposit_error,
		dataType: "json"
	});
}

function verify_deposit (amount) {
	$("#deposit-verify-amount").html(format_price(amount));
	$("#deposit-coins").hide();
	$("#deposit-verify").show();
}

// Click handler to submit a deposit.
$("#btn-submit-deposit").click(function () {
	deposit_alert_clear();

	var amount = strip_price($("#deposit-entry-total").text());

	// Clear deposit keypad box
	$("#deposit-entry-total").html(format_price(0.0));

	verify_deposit(parseFloat(amount));
	console.log('jflkdsa')
});

// Click handler to confirm a deposit.
$("#btn-confirm-deposit-yes").click(function () {
	$(this).blur();
	disable_button($(this));

	var amount = strip_price($("#deposit-verify-amount").text());
	handle_deposit(amount, 'manual');
});

// Click handler to reject a deposit.
$("#btn-confirm-deposit-no").click(function () {
	$("#deposit-verify").hide();
	$("#deposit-coins").show();

	enable_button($("#btn-confirm-deposit-yes"));
});

// Button press handler for the default deposit amount buttons
$(".btn-coin-deposit").click(function() {
	var input = full_strip_price($("#deposit-entry-total").text());
	var value = $(this).attr("id").split("-")[2];

	var output = 0;
	if (value !== "del") {
		output = (parseFloat(value) + parseFloat(input)) / 100.0;
	}

	$("#deposit-entry-total").html(format_price(output));
	calculate_user_new_balance();
});

// Switch to coin deposit mode
$("#btn-deposit-coins").click(function() {
	$("#deposit-main").hide();
	$("#deposit-complete").hide();
	$("#deposit-coins").show();
	$("#deposit-entry-total").html(format_price(0.0));
	calculate_user_new_balance();
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
					if ('error' in data) {
						alert_error(data.error);
						clear_umid_keypad();
					} else {
						window.location = '/terminal/' + manual_umid_enter;
					}				},
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
