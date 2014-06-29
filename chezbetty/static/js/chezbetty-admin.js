/* Functions to manipulate price strings and numbers.
 */
function format_price (price) {
	return "$" + price.toFixed(2);
}

function strip_price (price_str) {
	return price_str.replace(/^\s+|\s+$|\$/g, '');
}

function full_strip_price (price_str) {
	return price_str.replace(/^\s+|\s+$|\.|\$/g, '');
}

