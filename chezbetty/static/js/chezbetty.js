

function format_price (price) {
	return "$" + price.toFixed(2);
}

function strip_price (price_str) {
	return price_str.replace(/\$/g, '');
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