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
	return price_str.replace(/^\s+|\s+$|\$|,/g, '');
}

function full_strip_price (price_str) {
	return price_str.replace(/^\s+|\s+$|\.|\$|\,/g, '');
}

function parseIntZero (i) {
	var ret = parseInt(i);
	if (isNaN(ret)) return 0;
	return ret;
}

function parseFloatZero (f) {
	var ret = parseFloat(f);
	if (isNaN(ret)) return 0.0;
	return ret;
}

function alert_clear () {
	$("#alerts").empty();
}

// Callback when adding an item to the restock succeeds
function add_item_success (data) {
	if (data.status != "success") {
		if (data.status == "unknown_barcode") {
			alert_error("Could not find that item.");
		} else {
			alert_error("Error occurred.");
		}
	} else {
		// Make sure this item isn't already on the list
		if ($(".restock-"+data.type+"-" + data.id).length == 0) {
			// Add a new item

			// Update the "-X" with a unique row number
			num_rows = parseInt($("#row-count").val());
			row = data.data.replace(/-X/g, "-"+num_rows);

			// Add the row to the table
			$("#restock-table tbody").append(row);

			$("#row-count").val(num_rows+1)
			restock_update_line_total(num_rows);
		} else {
			// Already have this item in the table
			// Move it to the bottom so it's visible
			row_obj = $(".restock-"+data.type+"-"+data.id+":last");
			row_obj.insertAfter(".restock:last");
		}
	}
}

// Callback when adding to cart fails.
function add_item_fail () {
	alert_error("AJAX lookup failed.");
}

function add_item (barcode) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/barcode/"+barcode+"/json",
		success: add_item_success,
		error: add_item_fail
	});
}

// Callback when adding an item to the restock succeeds
function search_item_success (data) {
	alert_clear();
	$("#restock-search-notice").text("");
	$(".restock-search-addedrows").remove();

	if (data.status != "success") {
		alert_error("Error occurred.");
	} else {
		if (data.matches.length == 0) {
			// No matches tell user
			$("#restock-search-notice").text("No matches found.");
		} else if (data.matches.length == 1) {
			// One match just add it
			add_item(data.matches[0][2]);
			$("#restock-search-notice").text("One match found. Added " + data.matches[0][1] + ".");
		} else {
			for (i=0; i<data.matches.length; i++) {
				new_row = $("#restock-search-row-0").clone().attr("id", "restock-search-row-"+(i+1));
				new_row.find("button").each(function (index) {
					start_id = $(this).attr("id");
					splits = start_id.split("-");
					splits[splits.length-1] = i+1;
					new_id = splits.join("-");
					$(this).attr("id", new_id);
					$(this).attr("data-item", data.matches[i][2]);
				});
				new_row.find(".restock-search-row-name").text(data.matches[i][0] + ": " + data.matches[i][1]);
				new_row.addClass("restock-search-addedrows");
				new_row.show();

				if (data.matches[i][4]) {
					// This product is enabled
					$("#restock-search-table").append(new_row);
				} else {
					$("#restock-search-table-disabled").append(new_row);
				}
			}
		}
	}
}

// Callback when adding to cart fails.
function search_item_fail () {
	alert_error("AJAX lookup failed.");
}

function search_item (search_str) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/search/"+search_str+"/json",
		success: search_item_success,
		error: search_item_fail
	});
}


/******************************************************************************/
// USER PURCHASE ADD
// manually add purchase to user account
/******************************************************************************/

// Calculate the line totals and purchase total for user purchase add
function user_purchase_recalculate_totals () {
	var total = 0;
	$("#user-purchase-add-table-items tr:visible").each(function (index) {
		var quantity = parseInt($(this).find('.user-purchase-add-item-quantity').val());
		var price = parseFloat(strip_price($(this).find('.user-purchase-add-item-price').text()));

		// Update line total
		var line_total = quantity*price;
		$(this).find('.user-purchase-add-item-total').html(format_price(line_total));

		// Update running total
		total += line_total;
	});

	// Insert global total
	$("#user-purchase-add-items-total").html(format_price(total));
}

// Callback when adding an item to the user purchase succeeds
function user_purchase_add_item_success (data) {
	if (data.status != "success") {
		if (data.status == "unknown_barcode") {
			alert_error("Could not find that item.");
		} else {
			alert_error("Error occurred.");
		}
	} else {
		// Make sure this item isn't already on the list
		if ($("#user-purchase-add-item-"+data.type+"-" + data.id).length == 0) {
			// Add a new item

			new_row = $("#user-purchase-add-item").clone().attr("id", "user-purchase-add-item-"+data.type+"-" + data.id);
			new_row.find('.user-purchase-add-item-quantity').attr("name", "user-purchase-add-item-"+data.type+"-" + data.id);
			new_row.find(".user-purchase-add-item-title").text(data.name);
			new_row.find(".user-purchase-add-item-price").text(data.price);
			new_row.show();

			$("#user-purchase-add-table-items").append(new_row);

		} else {
			// Already have this item in the table
			// Take another barcode scan as an increase in quantity
			row_obj = $("#user-purchase-add-item-"+data.type+"-"+data.id+":last");
			quantity_obj = row_obj.find(".user-purchase-add-item-quantity");
			quantity_obj.val(parseInt(quantity_obj.val()) + 1);
		}

		user_purchase_recalculate_totals();
	}
}

// Callback when adding to cart fails.
function user_purchase_add_item_fail () {
	alert_error("AJAX lookup failed.");
}

function user_purchase_add_item (id) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/id/"+id+"/json",
		success: user_purchase_add_item_success,
		error: user_purchase_add_item_fail
	});
}

// Callback when adding an item to the restock succeeds
function search_item_only_success (data) {
	alert_clear();
	$("#user-search-notice-item").text("");
	$(".user-search-item-addedrows").remove();

	if (data.status != "success") {
		alert_error("Error occurred.");
	} else {
		if (data.matches.length == 0) {
			// No matches tell user
			$("#user-search-notice-item").text("No matches found.");
		} else if (data.matches.length == 1 && data.matches[0][0] == 'item') {
			// One match just add it
			user_purchase_add_item(data.matches[0][3]);
			$("#user-search-notice-item").text("One match found. Added.");
		} else {
			for (i=0; i<data.matches.length; i++) {
				if (data.matches[i][0] == 'item') {
					// Only look at items, not boxes

					var new_row = $("#user-search-item-row-0").clone().attr("id", "user-search-item-row-"+(i+1));
					new_row.find("button").each(function (index) {
						start_id = $(this).attr("id");
						splits = start_id.split("-");
						splits[splits.length-1] = i+1;
						new_id = splits.join("-");
						$(this).attr("id", new_id);
						$(this).attr("data-item", data.matches[i][3]);
					});
					new_row.find(".user-search-row-item-name").html(data.matches[i][0] + ': <a href="/admin/item/edit/'+data.matches[i][3]+'">'+data.matches[i][1]+'</a>');
					new_row.find(".user-search-row-item-stock").text('stock: ' + data.matches[i][5]);
					new_row.addClass("user-search-item-addedrows");
					new_row.show();

					$("#user-search-table-items").append(new_row);
				}
			}
		}
	}
}

// Callback when adding to cart fails.
function search_item_only_fail () {
	alert_error("AJAX lookup failed.");
}

function search_item_only (search_str) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/search/"+search_str+"/json",
		success: search_item_only_success,
		error: search_item_only_fail
	});
}

// Callback when looking up a user succeeds
function search_user_success (data, prefix) {
	alert_clear();
	$("#"+prefix+"-notice").text("");
	$("."+prefix+"-addedrows").remove();

	if (data.status != "success") {
		alert_error("Error occurred.");
	} else {
		if (data.matches.length == 0) {
			// No matches tell user
			$("#"+prefix+"-notice").text("No matches found.");
		} else {
			for (i=0; i<data.matches.length; i++) {
				var new_row = $("#"+prefix+"-row-0").clone().removeAttr("id");
				new_row.find("input[type=radio]").val(data.matches[i].id);
				if (i == 0) {
					new_row.find("input[type=radio]").attr('checked', 'checked');
				}
				new_row.find("."+prefix+"-row-name").text(data.matches[i].name);
				new_row.find("."+prefix+"-row-uniqname").text(data.matches[i].uniqname);
				new_row.find("."+prefix+"-row-umid").text(data.matches[i].umid);
				new_row.find("."+prefix+"-row-balance").html(format_price(data.matches[i].balance));
				new_row.addClass(prefix+"-addedrows");
				new_row.show();

				$("#"+prefix+"-table").append(new_row);
			}
		}
	}
}

// Callback when adding to cart fails.
function search_user_fail () {
	alert_error("AJAX lookup failed.");
}

function search_user (search_str, prefix) {
	$.ajax({
		dataType: "json",
		url: "/admin/user/search/"+search_str+"/json",
		success: function (data) {
			search_user_success(data, prefix);
		},
		error: search_user_fail
	});
}

/******************************************************************************/
// RESTOCK
/******************************************************************************/

function restock_update_line_total (row_id) {
	var row_obj = $("#restock-"+row_id);
	var quantity = parseIntZero($("#restock-quantity-"+row_id).val());
	var wholesale = parseFloatZero($("#restock-wholesale-"+row_id).val());
	var coupon = parseFloatZero($("#restock-coupon-"+row_id).val());
	var salestax = $("#restock-salestax-"+row_id).prop("checked");
	var btldep = $("#restock-bottledeposit-"+row_id).prop("checked");
	var itemcount = parseInt($("#restock-itemcount-"+row_id).val());
	var total_obj = $("#restock-total-"+row_id);

	var total = quantity * (wholesale - coupon);
	if (salestax) {
		total *= 1.06
	}
	if (btldep) {
		total += (0.10 * itemcount * quantity)
	}

	total_obj.val(total.toFixed(2));

	// Make sure the total is up to date
	calculate_total();
}

// Function to add up the items in a cart to display the total.
function calculate_total () {
	var subtotal = 0.0;
	var coupon_total = 0.0;

	$(".restock").each(function (index) {
		var price = parseFloatZero($(this).find(".restock-total").val());
		subtotal += price;
		var coupon_price = parseFloatZero($(this).find(".restock-coupon").val());
		var quantity = parseIntZero($(this).find(".restock-quantity").val());
		coupon_total += (coupon_price * quantity);
	});

	// Get the aggregate cost that should be split among all items.
	var global_cost = parseFloatZero($("#restock-globalcost").val());
	var donation = parseFloatZero($("#restock-donation").val());
	var total = subtotal + global_cost - donation;

	$("#restock-subtotal").html(format_price(subtotal));
	$("#restock-coupon-total").html(format_price(coupon_total));
	$("#restock-total").html(format_price(total));
}

/******************************************************************************/
// ADJUST USER BALANCE
/******************************************************************************/

function adjust_user_balance_update () {
	var sender = $('input[name=sender-search-choice]:checked');
	var sender_balance = parseFloat(strip_price(sender.closest('tr').find('.sender-search-row-balance').text()));
	var recipient = $('input[name=recipient-search-choice]:checked');
	var recipient_balance = parseFloat(strip_price(recipient.closest('tr').find('.recipient-search-row-balance').text()));
	var amount = parseFloat($("#balance-change-amount").val() || 0);

	if (!isNaN(sender_balance)) {
		var new_sender = sender_balance - amount;
		$("#sender-balance").html(format_price(new_sender));
	} else {
		$("#sender-balance").html('');
	}

	if (!isNaN(recipient_balance)) {
		var new_recipeint = recipient_balance + amount;
		$("#recipient-balance").html(format_price(new_recipeint));
	} else {
		$("#recipient-balance").html('');
	}
}

/******************************************************************************/
// REQUESTS
/******************************************************************************/

function request_delete_success (data) {
	if (data.status == "success") {
		$("#request-" + data.request_id).remove();
	} else {
		alert_error("Could not remove request.");
	}
}

function request_delete_fail (data) {
	alert_error("Could not remove request.");
}
