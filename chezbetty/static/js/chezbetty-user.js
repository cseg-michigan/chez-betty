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
