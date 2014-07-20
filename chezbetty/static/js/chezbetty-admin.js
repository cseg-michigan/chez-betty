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

function parseFloatZero (f) {
	var ret = parseFloat(f);
	if (isNaN(ret)) return 0.0;
	return ret;
}

function alert_clear () {
	$("#alerts").empty();
}

function alert_error (error_str) {
	html = '<div class="alert alert-danger" role="alert">'+error_str+'</div>';
	$("#alerts").empty();
	$("#alerts").html(html);
}

// Callback when adding an item to the cart succeeds
function add_item_success (data) {
	if (data.status != "success") {
		if (data.status == "unknown_barcode") {
			alert_error("Could not find that item.");
		} else {
			alert_error("Error occurred.");
		}
	} else {
		// Make sure this item isn't already on the list
		if ($("#restock-"+data.type+"-" + data.id).length == 0) {
			// Add a new item
			$("#restock-table tbody").append(data.data);
			attach_keypad();
		} else {
			// Already have this item in the table
			// Take another barcode scan as an increase in quantity
			quantity_obj = $("#restock-"+data.type+"-quantity-" + data.id);
			quantity_obj.val(parseInt(quantity_obj.val()) + 1);
			restock_update_total_quantity(quantity_obj);
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

// Function to add up the items in a cart to display the total.
function calculate_total () {
	total = 0.0;
	$(".item-total input").each(function (index) {
		var price = parseFloat($(this).val());
		var fields = $(this).attr("id").split("-");

		// Check if we should add sales tax
		fields[2] = "salestax";
		if ($("#"+fields.join("-")+":checked").length == 1) {
			price *= 1.06;
		}

		total += price;
	});

	$("#restock-total").html(format_price(total));
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
