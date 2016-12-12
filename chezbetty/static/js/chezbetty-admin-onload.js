
// Make the Demo Mode checkbox in the sidebar a pretty on/off slider
$(".admin-switch").bootstrapSwitch();

function ajax_bool (js_obj, object, field, id, state) {
	var url = "/admin/ajax/bool/"+object+"/"+id+"/"+field+"/"+state;
	$.ajax({
		url: url,
		context: js_obj,
		success: toggle_state_success,
		error: toggle_state_fail
	});
}

$(".ajax-bool-switch").on('switchChange.bootstrapSwitch', function (event, state) {
	var fields = $(this).attr("id").split("-");
	ajax_bool($(this), fields[2], fields[3], fields[4], state);
});

$(".ajax-bool-btn").on('click', function () {
	var fields = $(this).attr("id").split("-");
	ajax_bool($(this), fields[2], fields[3], fields[4], fields[5]);
});

function toggle_state_success (data) {
	var parent = $("#"+$(this).attr("data-parent"));

	if ($(this).hasClass('require-refresh')) {
		location.reload();

	} else if ($(this).hasClass('toggle-disabled')) {
		if ($(this).prop("checked")) {
			parent.removeClass("disabled-row");
		} else {
			parent.addClass("disabled-row");
		}

	} else if ($(this).hasClass("delete-entry")) {
		parent.hide();
	}
}

function toggle_state_fail (data) {
	alert_error("Failed to save toggle state.");
}

function toggle_enabled (type, btn) {
	btn_type = btn.attr("id").split("-")[1];
	id = btn.attr("id").split("-")[3];
	row = $("#"+type+"-" + id);

	if (btn_type === "disable") {

		// Mark the row to be disabled upon submit
		row.children("#"+type+"-enabled-"+id).val("0");

		// Gray out the row to show it will be deleted
		$("#"+type+"-" + id + " input:text").attr("disabled", "disabled");

		// Hide the delete button
		btn.hide();

		// Display the undo button
		$("#btn-enable-"+type+"-" + id).show();

	} else if (btn_type === "enable") {

		// Mark the user as enabled
		row.children("#"+type+"-enabled-"+id).val("1");

		// Un-disable the boxes in the row
		$("#"+type+"-" + id + " input:text").removeAttr("disabled");

		// Hide the undo button
		btn.hide();

		// Show the delete button again
		$("#btn-disable-"+type+"-" + id).show();
	}
}



// General class that allows values to be fetched on-demand
$(".ajaxed_field").each(function ajaxed_each (index) {
	var url = "/admin/ajax/field/" + $(this).attr('id');
	$.ajax({
		url: url,
		context: this,
		success: function ajaxed_field_success (data) {
			$(this).html(data.html);
		},
		error: function ajaxed_field_error (data) {
			$(this).text('<Error>');
		},
	});
});


// ANNOUNCEMENTS

function tweet_char_count () {
  var len = $('#tweet').val().length;
  var rem = 140 - len;
  $('#tweet-char-count').text('Characters Remaining: ' + rem);
  if (rem > 0) {
    $('#tweet-char-count').css('color', 'black');
  } else {
    $('#tweet-char-count').css('color', 'red');
  }
}

$("#tweet").on('change keyup paste input propertychange', tweet_char_count);

// Need to call on page load too b/c browser may remember form contents
if ($('#tweet').length > 0) {
	tweet_char_count();
}


// ITEMS

$("#new-item").click(function () {
	// Instead of counting each time, just keep the number of lines around
	// in a hidden element.
	var item_lines_count = parseInt($("#item-count").val());

	// Copy row 0 to create a new row
	container = $("#item-0").clone().attr("id", "item-"+item_lines_count);
	container.find("*").each(function (index) {
		// Update the ID to the next number
		id = $(this).attr("name");
		if (id) {
			name_pieces = id.split("-");
			name_pieces[name_pieces.length-2] = item_lines_count;
			new_id = name_pieces.join("-");
			$(this).attr("id", "box-" + new_id);
			$(this).attr("name", new_id);
			if ($(this).is(":checkbox")) {
				// Clear checkmarks
				$(this).prop("checked", "");
			} else {
				// Clear the value if there is text in the first row already
				$(this).val("");
			}
			if (name_pieces[2] == 'barcode') {
				$(this).on("input", barcode_check_fn);
				// Since we clone the input, we need to trigger to clear its coloring
				$(this).trigger("input");
			}
		}
	});

	// Add the new row to the page
	$("#newitem-rows").append(container);

	// Update the number of new items to be added
	$("#item-count").val(item_lines_count+1);
});


$(".edit-item-row").on("click", "button", function () {
	toggle_enabled("item", $(this));
});

$(".edit-box-row").on("click", "button", function () {
	toggle_enabled("box", $(this));
});

$(".edit-user-row").on("click", "button", function () {
	toggle_enabled("user", $(this));
});

$(".edit-vendor-row").on("click", "button", function () {
	toggle_enabled("vendor", $(this));
});

$(".edit-announcement-row").on("click", "button", function () {
	toggle_enabled("announcement", $(this));
});

barcode_check_fn = function () {
	var validator = new Barcoder();

	if ($(this).val() == '') {
		$(this).css("backgroundColor", "inherit");
	} else if (validator.validate($(this).val()).isValid) {
		$(this).css("backgroundColor", "#98FB98");
	} else {
		$(this).css("backgroundColor", "#FF9999");
	}
};

$(".barcode-check").on("input", barcode_check_fn);

// Update markup
$("#edit-items").on("input", "input:text", function () {
	var id = $(this).attr("id").split("-")[2];
	var price = parseFloat($("#item-price-"+id).val());
	var wholesale = parseFloat($("#item-wholesale-"+id).val());

	var markup = (((price/wholesale) - 1.0) * 100.0).toFixed(2);
	$("#item-markup-"+id).text(markup + "%");
	$("#item-markup-"+id).attr("data-value", markup);
});

// ADJUST USER BALANCE
$('.user-balance-change-participant').on('change', 'input[name=sender-search-choice]', adjust_user_balance_update);
$('.user-balance-change-participant').on('change', 'input[name=recipient-search-choice]', adjust_user_balance_update);
$("#balance-change-amount").on("input", adjust_user_balance_update);

// RESTOCK

$(".event-date-picker").datetimepicker({
	format: "Y/m/d H:iO",
	inline: true
});

$("#restock-table tbody tr").each(function () {
	var row_id = $(this).attr("id").split("-")[1];
	restock_update_line_total(row_id);
});

$(".restock-manual").on("click", function () {
	var type = $(this).attr("id").split("-")[2];
	if (type == "item" || type == "box") {
		add_item($("#restock-manual-"+type+"-select").val());
	} else if (type == "search") {
		search_item($("#restock-manual-"+type+"-input").val());
	}
});

$("#restock-table").on("click", "input:checkbox", function () {
	restock_update_line_total($(this).attr("id").split("-")[2]);
});

// When the per item cost changes, update the line item total
$("#restock-table").on("input", "input:text", function () {
	restock_update_line_total($(this).attr("id").split("-")[2]);
});

// Add a searched for item to the restock table
$(".restock-search-table").on("click", "button", function () {
	var barcode = $(this).attr("data-item");
	add_item(barcode);
});

// USER PURCHASE ADD

$(".user-search-button").on("click", function () {
	var prefix = $(this).attr('data-prefix');
	search_user($("#"+prefix+"-string").val(), prefix);
});

$("#user-purchase-add-search-item-button").on("click", function () {
	search_item_only($("#user-purchase-add-search-item").val());
});

$("#user-search-table-items").on("click", ".user-search-item-row-button", function () {
	user_purchase_add_item($(this).attr('data-item'));
});

$("#user-purchase-add-table-items").on("input", "input:text", function () {
	user_purchase_recalculate_totals();
});

// BOXES

$("#new-box-table").on("input", function () {
	var base = $("#box-general-name").val();
	var variants = $("#box-variants").val();
	var volume = $("#box-volume").val();
	var quantity = $("#box-quantity").val();

	var name = base;
	if (variants.length) {
		name += " (" + variants + ")";
	}
	if (volume.length) {
		name += " (" + volume.replace(/ /g, "") + ")";
	}
	if (quantity.length) {
		name += " " + quantity + " Pack";
	}
	$("#box-name").val(name);
});

$(".box-subitem, #newitems").on("input", "input:text", function () {
	var row_id = $(this).attr("id").split("-")[2];
	var base = $("#box-item-"+row_id+"-general").val();
	var volume = $("#box-item-"+row_id+"-volume").val();

	var name = base;
	if (volume.length) {
		name += " (" + volume.replace(/ /g, "") + ")";
	}
	$("#box-item-"+row_id+"-name").val(name);
});

$(".box-subitem").on("change", "select", function () {
	var row_id = $(this).attr("id").split("-")[2];
	var item_val = $(this).val();
	if (item_val == "new") {
		$("#box-item-"+row_id+"-new").show();
	} else {
		$("#box-item-"+row_id+"-new").hide();
	}
});

$("#box-new-subitem").click(function () {
	// Instead of counting each time, just keep the number of lines around
	// in a hidden element.
	var item_lines_count = parseInt($("#box-subitem-count").val());

	// Copy row 0 to create a new row
	container = $("#box-item-0").clone().attr("id", "new-item-"+item_lines_count);
	container.find("*").each(function (index) {
		// Update the ID to the next number
		id = $(this).attr("id");
		if (id) {
			name_pieces = id.split("-");
			name_pieces[name_pieces.length-2] = item_lines_count;
			new_id = name_pieces.join("-");
			$(this).attr("id", new_id);
			$(this).attr("name", new_id);
			if ($(this).is(":checkbox")) {
				// Reset the checkmark so new products are enabled by default
				$(this).prop("checked", "checked");
			} else {
				// Clear the value if there is text in the first row already
				$(this).val("");
			}
			if (name_pieces[3] == 'barcode') {
				$(this).on("input", barcode_check_fn);
				// Since we clone the input, we need to trigger to clear its coloring
				$(this).trigger("input");
			}
		}
	});

	// Add the new row to the page
	$("#box-subitem-rows").append(container);

	// Hide the new item fields by default
	$("#box-item-"+item_lines_count+"-new").hide();

	// Update the number of new items to be added
	$("#box-subitem-count").val(item_lines_count+1);
});


$(".request-delete").click(function () {
	var request_id = $(this).attr("id").split("-")[3];

	$.ajax({
		url: "/admin/request/delete/" + request_id,
		success: request_delete_success,
		error: request_delete_fail
	});
});

// Check that the number of subitems in a box matches the
// total number of items that should be in that box.
$('#box_add_form').submit(function check_submit(evt) {
	evt.preventDefault();

	var box_qty = parseInt($("#box-quantity").val());
	var sub_qty = 0;
	$(".subitem-quantity").each(function(index) {
		sub_qty += parseInt($(this).val());
	});
	if (box_qty != sub_qty) {
		alert("Sum of subitem quantities ("+sub_qty+") must match box quantity ("+box_qty+")");
		return false;
	}

	$(this).unbind('submit').trigger('submit');
});


//
// Tags
//

$("#btn-tag-new").click(function () {
	var new_tag = $("#tag-new").val();

	$.ajax({
		url: "/admin/ajax/new/tag/" + new_tag,
		success: tag_new_success,
		error: tag_new_fail
	});
});

function tag_new_success (data) {
	// Add the new tag to the existing tags box on the page
	add_tag_to_item(data['id'], $("#item-id").val());

	$("#tag-new").val("");
}

function tag_new_fail () {
	alert_error("Could not create a new tag.");
}

$(".tag-to-add").click(function () {
	var tag_id = $(this).attr("data-tag-id");
	var item_id = $("#item-id").val();
	add_tag_to_item(tag_id, item_id);
});

function add_tag_to_item (tag_id, item_id) {
	$.ajax({
		url: "/admin/ajax/connection/item/tag/" + item_id + "/" + tag_id,
		success: tag_connected_success,
		error: tag_connected_fail
	});
}

function tag_connected_success (data) {
	tag_name = $("#tag-"+data['arg2']).val();
	$("#tag-"+data['arg2']).remove();

	$("#item-existing-tags").append(' <button type="button" \
		class="btn btn-default" data-item-tag-id="' + data['item_tag_id'] + '">'
		+ data['tag_name'] + '</button>');
}

function tag_connected_fail () {
	alert_error("Could not add that tag to the item.");
}

$("#item-existing-tags").on("click", "button", function () {
	var item_tag_id = $(this).attr("data-item-tag-id");

	$.ajax({
		url: "/admin/ajax/bool/itemtag/" + item_tag_id + "/deleted/true",
		context: $(this),
		success: tag_disconnected_success,
		error: tag_disconnected_fail
	});
});

function tag_disconnected_success (data) {
	$(this).remove();
}

function tag_disconnected_fail () {
	alert_error("Could not remove the tag from the item.");
}

//
// Reimbursements
//

$('#reimbursee').change(function () {
	var amount = $('#reimbursee option:selected').attr('data-amount');
	$('#reimbursement-amount').val(amount);
})

//
// Deletions
//

$(".btn-delete").click(function () {
	var object = $(this).attr('data-object');
	var id = $(this).attr('data-id');
	var to_remove = $(this).attr('data-to-remove');

	$.ajax({
		url: '/admin/ajax/delete/' + object + '/' + id,
		success: function (data) {
			$('#' + to_remove).remove();
		},
		error: function () {
			alert_error('Could not delete that object.');
		}
	});
});


// filterable tables
$('.filterable').each(function (table_index) {

	var table = $(this);

	// Mark the original body as the one we are going to filter
	table.find("tbody").addClass("filtered-body");

	// Add the row of filter dropdowns
	// jquery will auto create a tbody element in the wrong place,
	// so we get in there first and do it correctly.
	var tbody = $("<tbody></tbody>");
	var tr = $('<tr class="filters"></tr>');
	table.prepend(tbody);
	tbody.append(tr);

	// Build the dropdowns
	$(this).find("th").each(function (th_index) {
		var td = $("<td></td>").appendTo(tr);
		if ($(this).hasClass("filterable-row")) {
			var select = $('<select><option value=""></option></select>')
				.appendTo(td)
				.attr("xindex", th_index+1)
				.on("change", function () {
					var val = $(this).val();
					xindex = $(this).attr("xindex");
					val = $(this).val();

					$(this).closest("table").find("tbody.filtered-body tr").show();

					$(this).closest("table").find("tr.filters td").each(function (i) {
						select = $(this).find("select");
						if (select.length > 0) {
							val = select.val();
							if (val != "") {
								$(this).closest("table").find("tbody.filtered-body tr:visible").each(function () {
									td = $(this).find("td:nth-child("+(i+1)+")");
									value = td.attr("data-value");
									if (!value) {
										value = td.text();
									}
									if (value == val) {
										$(this).show();
									} else {
										$(this).hide();
									}
								});
							}

						}
					});
				});

			var elements = [];
			table.find("tbody.filtered-body tr td:nth-child("+(th_index+1)+")").each(function () {
				value = $(this).attr("data-value");
				if (!value) {
					value = $(this).text();
				}
				if ($.inArray(value, elements) == -1) {
					elements.push(value);
					select.append('<option value="'+value+'">'+value+'</option>');
				}
			});

		}

	});
});



//
// Check for unsaved data in forms
//
var serialized_form_clean;
var clicked_submit = false;

// When the page load we get the values serialize
serialized_form_clean = $("form").serialize().split("&").sort().join("&");

// Before we leave the page we now compare between the new form values and the orignal
window.onbeforeunload = function (e) {
    var serialized_form_dirty = $("form").serialize().split("&").sort().join("&");
    if (serialized_form_clean != serialized_form_dirty && !clicked_submit) {
        return "You are about to leave a page where you have not saved the data.";
    }
};

$("button:submit").click(function () {
	clicked_submit = true;
});


//
// Make sticky column headers work
//

$('.sticky').stickyTableHeaders({fixedOffset: $('.navbar')});

