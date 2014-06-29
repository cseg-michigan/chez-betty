/* Functions to manipulate price strings and numbers.
 */
function format_price (price) {
	p = price.toFixed(2);

	if (p < 0) {
		return '<span class="negative">-$' + (p*-1.0) + '</span>';
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

// Callback when adding an item to the cart succeeds
function add_item_success (data) {

	// Make sure this item isn't already on the list
	if (!$("#restock-item-" + data.id).length) {
		// Add a new item
		$("#restock-table tbody").append(data.item_restock_html);
	}

	calculate_total();
}

function add_item (barcode) {
	$.ajax({
		dataType: "json",
		url: "/admin/item/"+barcode+"/json",
		success: add_item_success,
		error: add_item_fail
	});
}
