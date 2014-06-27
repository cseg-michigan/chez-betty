

function format_price (price) {
	return "$" + price.toFixed(2);
}

function strip_price (price_str) {
	return price_str.replace(/\$/g, '');
}

function add_item_success (data) {
	alert_clear();
	
	// First, if this is the first item hide the empty order row
	$("#purchase-empty").hide();

	// Check if this item is already present. In that case we only
	// need to increment the quantity and price
	if ($("#purchase-item-" + data.id).length) {
		item_row = $("#purchase-item-" + data.id);

		// Increment the quantity
		quantity = parseInt(item_row.children(".item-quantity").text()) + 1;
		item_price = parseFloat(item_row.children(".item-price-single").text());

		item_row.children(".item-quantity").text(quantity);
		item_row.children(".item-price").text(format_price(quantity*item_price));

	} else {
		// Add a new item
		$("#purchase_table tbody").append(data.item_row_html);
	}

	calculate_total();
}

function add_item_fail () {
	alert_error("Could not find that item.");
}

function add_item (item_id) {
	$.ajax({
		dataType: "json",
		url: "/item/"+item_id+"/json",
		success: add_item_success,
		error: add_item_fail
	});
}

function calculate_total () {
	total = 0;
	$("#purchase_table tbody tr:visible").each(function (index) {
		if ($(this).attr('id') != "purchase-empty") {
			line_total = parseFloat(strip_price($(this).children('.item-price').text()));
			total += line_total;
		}
	});

	$("#purchase-total").text(format_price(total));
}

function alert_clear () {
	$("#alerts").empty();
}

function alert_error (error_str) {
	$("#alerts").empty();
	$("#alerts").html('<div class="alert alert-danger" role="alert">' + error_str + '</div>');
}

