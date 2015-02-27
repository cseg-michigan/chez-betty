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

function alert_success (success_str) {
	html = '<div class="alert alert-success" role="alert">'+success_str+'</div>';
	alert_clear();
	$("#alerts").html(html);
}

function alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	alert_clear();
	$("#alerts").html(html);
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
			attach_keypad();
			restock_update_line_total(num_rows);
		} else {
			// Already have this item in the table
			// Take another barcode scan as an increase in quantity
			row_obj = $(".restock-"+data.type+"-"+data.id+":last");
			quantity_obj = row_obj.find(".quantity input");
			quantity_obj.val(parseInt(quantity_obj.val()) + 1);
			restock_update_line_total(row_obj.attr("id").split("-")[1]);
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
		url: "/admin/item/"+barcode+"/json",
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
			$("#restock-search-notice").text("One match found. Added.");
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
				new_row.find(".restock-search-row-name").each(function () {
					$(this).text(data.matches[i][0] + ": " + data.matches[i][1]);
				});
				new_row.addClass("restock-search-addedrows");
				new_row.show();

				$("#restock-search-table").append(new_row);
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
	var total = 0.0;
	var coupon_total = 0.0;

	$(".restock").each(function (index) {
		var price = parseFloatZero($(this).find(".restock-total").val());
		total += price;
		var coupon_price = parseFloatZero($(this).find(".restock-coupon").val());
		var quantity = parseIntZero($(this).find(".restock-quantity").val());
		coupon_total += (coupon_price * quantity);
	});

	$("#restock-total").html(format_price(total));
	$("#restock-coupon-total").html(format_price(coupon_total));
}

function update_new_balance () {
	start = parseFloat(strip_price($(".current-balance:visible").text()));
	amount = parseFloat($("#balance-change-amount").val());
	if (isNaN(amount)) {
		amount = 0.0;
	}
	new_balance = format_price(start + amount);
	$("#new_balance").html(new_balance);
}

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
