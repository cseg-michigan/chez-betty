
function prettydate (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
	$(this).switchClass('date', 'prettydate');
}
$(".date").each(prettydate);

// Make the Demo Mode checkbox in the sidebar a pretty on/off slider
$(".admin-switch").bootstrapSwitch();

function ajax_bool (js_obj, object, field, id, status) {
	var url = "/admin/ajax/bool/"+object+"/"+id+"/"+field+"/"+status;
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
	var parent = $("#"+$(this).attr("data-parent"))

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
	row = $("#"+type+"-" + id)

	if (btn_type == "disable") {

		// Mark the row to be disabled upon submit
		row.children("#"+type+"-enabled-"+id).val("0");

		// Gray out the row to show it will be deleted
		$("#"+type+"-" + id + " input:text").attr("disabled", "disabled");

		// Hide the delete button
		btn.hide();

		// Display the undo button
		$("#btn-enable-"+type+"-" + id).show();

	} else if (btn_type == "enable") {

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

// single use button

function button_singleuse_success (data) {
	if (data["status"] == "success") {
		$(this).hide();
		alert_success(data["msg"]);
	} else {
		alert_error(data["msg"]);
	}
}

function button_singleuse_fail (data) {
	alert_error("Button click failed.");
}

$(".btn-ajax_singleuse").on('click', function () {
	var url = $(this).attr("data-url");
	$.ajax({
		url: url,
		context: $(this),
		success: button_singleuse_success,
		error: button_singleuse_fail
	});
});


// General class that allows values to be fetched on-demand
$(".ajaxed_field").each(function ajaxed_each (index) {
	var url = "/admin/ajax/field/" + $(this).attr('id');
	$.ajax({
		url: url,
		context: this,
		success: function ajaxed_field_success (data) {
			$(this).html(data['html']);
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
};

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
			if (name_pieces[3] == 'barcode') {
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

	attach_keypad();
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

// Add a new row to the add items form
$("#btn-items-add-row").click(function () {

	// Instead of counting each time, just keep the number of lines around
	// in a hidden element.
	var item_lines_count = parseInt($("#new-items-number").val());

	// Copy row 0 to create a new row
	container = $("#new-item-0").clone().attr("id", "new-item-"+item_lines_count);
	container.find("input").each(function (index) {
		// Update the ID to the next number
		id = $(this).attr("id");
		name_pieces = id.split("-");
		name_pieces[name_pieces.length-1] = item_lines_count;
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
		if (name_pieces[1] == 'barcode') {
			$(this).on("input", barcode_check_fn);
			// Since we clone the input, we need to trigger to clear its coloring
			$(this).trigger("input");
		}
	});

	// Add the new row to the page
	$("#new-items").append(container);

	// Update the number of new items to be added
	$("#new-items-number").val(item_lines_count+1);

	attach_keypad();
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

$("#select-user").change(function () {
	user_id = $("#select-user option:selected").val();

	// Hide all current balances
	$(".current-balance").hide();

	// Show the correct current balance for this user
	$("#current-balance-"+user_id).show();

	update_new_balance();
});

$("#balance-change-amount").on("input", function () {
	update_new_balance();
});

$("#edit-items").click(function () {
	alert_clear();
});

// Update markup
$("#edit-items").on("input", "input:text", function () {
	var id = $(this).attr("id").split("-")[2];
	var price = parseFloat($("#item-price-"+id).val());
	var wholesale = parseFloat($("#item-wholesale-"+id).val());

	var markup = (((price/wholesale) - 1.0) * 100.0).toFixed(2);
	$("#item-markup-"+id).text(markup + "%");
	$("#item-markup-"+id).attr("data-value", markup);
});

// RESTOCK

$("#restock-date").datetimepicker({
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
$("#restock-search-table").on("click", "button", function () {
	var barcode = $(this).attr("data-item");
	add_item(barcode);
});


// BOXES

$("#new-box-table").on("input", "input:text", function () {
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
		name += " " + quantity + " Pack"
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

	attach_keypad();
});


$(".request-delete").click(function () {
	var request_id = $(this).attr("id").split("-")[3];

	$.ajax({
		url: "/admin/request/delete/" + request_id,
		success: request_delete_success,
		error: request_delete_fail
	});
})




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
					})
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

