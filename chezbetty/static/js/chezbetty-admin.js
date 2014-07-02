/* Functions to manipulate price strings and numbers.
 */
function format_price (price) {
	p = price.toFixed(2);

	console.log(p*-1.0)

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
	if (data.status == "unknown_barcode") {
		console.log("Could not find that item.");
	} else {
		// Make sure this item isn't already on the list
		if ($("#restock-item-" + data.id).length == 0) {
			// Add a new item
			$("#restock-table tbody").append(data.data);
		}
	}
}

// Callback when adding to cart fails.
function add_item_fail () {
	console.log("Could not find that item.");
}

function add_item (barcode) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/"+barcode+"/json",
		success: add_item_success,
		error: add_item_fail
	});
}

function calculate_price (price_str) {
	divides = price_str.split("/");
	if (divides.length > 1) {
		price = parseFloat(divides[0]) / parseInt(divides[1]);
	} else {
		price = parseFloat(divides[0]);
	}
	if (isNaN(price)) {
		price = 0.0;
	}
	return price;
}

// Function to add up the items in a cart to display the total.
function calculate_total () {
	total = 0.0;
	$(".item-cost input").each(function (index) {
		price = calculate_price($(this).val());
		item_id = $(this).attr("id").split("-")[2];

		// Check if we should add sales tax
		if ($("#restock-salestax-"+item_id+":checked").length == 1) {
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
