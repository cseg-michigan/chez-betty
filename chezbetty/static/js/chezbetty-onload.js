

// Click handler to remove an item from a purchase.
$("#purchase_table tbody").on('click', '.btn-remove-item', function () {
	$(this).parent().parent().slideUp().remove();

	// Check if the cart is empty and put the "Empty Order" row back in
	if ($("#purchase_table tbody tr:visible").length == 0) {
		$("#purchase-empty").show();
	}

	// Re-calculate the total
	calculate_total();
});

$("#btn-add-item").click(function () {
	items = [{"name": "Coke",
	        "price": 1.33,
	        "id": 2739821,
	        "item_html": '<tr id="purchase-item-2739821" class="purchase-item"><td class="item-actions"><button type="button" class="btn btn-danger btn-remove-item">X</button></td>   <td class="item-title">Coke</td>  <td class="item-quantity">1</td>  <td class="item-price">$1.33</td>  <td class="hidden item-price-single">1.33</td></tr>'},

           {"name": "Coffee",
	        "price": 5.43,
	        "id": 88,
	        "item_html": '<tr id="purchase-item-88" class="purchase-item">  <td class="item-actions"><button type="button" class="btn btn-danger btn-remove-item">X</button></td>  <td class="item-title">Coffee</td>  <td class="item-quantity">1</td>  <td class="item-price">$5.43</td>  <td class="hidden item-price-single">5.43</td></tr>'},

           {"name": "Peach",
	        "price": 0.74,
	        "id": 1234,
	        "item_html": '<tr id="purchase-item-1234" class="purchase-item">  <td class="item-actions"><button type="button" class="btn btn-danger btn-remove-item">X</button></td>   <td class="item-title">Peach</td>  <td class="item-quantity">1</td>  <td class="item-price">$0.74</td>  <td class="hidden item-price-single">0.74</td></tr>'}];
	
	item = items[Math.floor((Math.random()*items.length))];

	// First, if this is the first item hide the empty order row
	$("#purchase-empty").hide();

	// Check if this item is already present. In that case we only
	// need to increment the quantity and price
	if ($("#purchase-item-" + item.id).length) {
		item_row = $("#purchase-item-" + item.id);

		// Increment the quantity
		quantity = parseInt(item_row.children(".item-quantity").text()) + 1;
		item_price = parseFloat(item_row.children(".item-price-single").text());

		item_row.children(".item-quantity").text(quantity);
		item_row.children(".item-price").text(format_price(quantity*item_price));

	} else {
		// Add a new item
		$("#purchase_table tbody").append(item.item_html);
	}

	calculate_total();

});
