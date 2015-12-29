








//
// Logout
//

// Check for items in the cart on a logout and submit the purchase
$('#logout-button').click(function () {

	if ($("#purchase-total").length) {
		// This is the purchase page
		cart_total = parseFloat(strip_price($("#purchase-total").text()));
		if (cart_total > 0) {
			// Need to pay for these items before logging out.
			submit_purchase(this, purchase_andlogout_success, purchase_error);
			return false;
		}
	}

});
