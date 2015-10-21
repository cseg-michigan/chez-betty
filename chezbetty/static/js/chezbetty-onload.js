/*
 * Chez Betty Javascript that attaches functions to event handlers.
 *
 */


$(".date").each(function (index) {
	d = new Date($(this).text());
	s = $.format.date(d, "MMM d, yyyy") + " at " + $.format.date(d, "h:mm a");
	$(this).text(s);
});


// Click handler to submit a deposit.
$(".btn-submit-deposit").click(function () {
	$(this).blur();
	alert_clear();

	disable_button($(this));

	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.amount = strip_price($("#keypad-total").text());

	// What account to deposit to?
	fields = $(this).attr("id").split("-");
	deposit.account = fields[2];
	if (deposit.account == "pool") {
		deposit.pool_id = fields["3"];
	}

	// Post the deposit to the server
	$.ajax({
		type: "POST",
		url: "/terminal/deposit/new",
		data: deposit,
		success: deposit_success,
		error: deposit_error,
		dataType: "json"
	});
});

// Click handler to submit a deposit.
$(".btn-edit-deposit").click(function () {
	$(this).blur();
	alert_clear();

	disable_button($(this));

	deposit = {};
	deposit.umid = $("#user-umid").text();
	deposit.amount = strip_price($("#keypad-total").text());
	deposit.old_event_id = $("#event_id").text();

	// What account to deposit to?
	fields = $(this).attr("id").split("-");
	deposit.account = fields[2];
	if (deposit.account == "pool") {
		deposit.pool_id = fields["3"];
	}

	// Post the deposit to the server
	$.ajax({
		type: "POST",
		url: "/terminal/deposit/edit/submit",
		data: deposit,
		success: deposit_success,
		error: deposit_error,
		dataType: "json"
	});
});

// Button press handler for the default deposit amount buttons
$("#default_values_wrapper").on("click", "button", function() {
	var value = $(this).attr("id").split("-")[2];

	if (value == "custom") {
		$("#default_values_wrapper").hide();
		$("#keypad_wrapper").show();
		$("#keypad-total").html(format_price(0.0));
		return;
	}

	$("#keypad-total").html(format_price(parseFloat(value)));
});

// Button press handler for the keypad
$("#keypad").on("click", "button", function () {
	var input = full_strip_price($("#keypad-total").text());
	var value = $(this).attr("id").split("-")[2];

	if (value == "del") {
		input = input.slice(0, input.length-1);
	} else {
		input += value;
	}

	var output = parseFloat(input) / 100.0;

	$("#keypad-total").html(format_price(output));
});

var manual_umid_enter = '';
var manual_umid_timeout = -1;
// Button press handler for the umid keypad
$("#keypad-umid").on("click", "button", function () {

	if (manual_umid_enter.length < 8) {
		// If we haven't gotten enough of a UMID yet then we are cool
		// to keep taking inputs

		var value = $(this).attr("id").split("-")[2];
		if (value == 'del') {
			var num = manual_umid_enter.length;
			if (num == 0) {
				return;
			}
			$("#keypad-umid-status block:eq("+(8-num)+")").removeClass("umid-status-blue");
			manual_umid_enter = manual_umid_enter.slice(0, -1);
		} else if (value == 'clear') {
			clear_umid_keypad();
		} else {
			manual_umid_enter += value;

			var num = manual_umid_enter.length;
			$("#keypad-umid-status block:eq("+(8-num)+")").addClass("umid-status-blue");
		}

		if (manual_umid_enter.length == 8) {
			$.ajax({
				type: "POST",
				url: "/terminal/check",
				data: {'umid': manual_umid_enter},
				success: function (data) {
					if (data.status == 'success') {
						window.location = '/terminal/purchase/' + manual_umid_enter;
					} else {
						clear_umid_keypad();
					}
				},
				error: function (data) {
					if (manual_umid_timeout >= 0) {
						clearTimeout(manual_umid_timeout);
					}
					clear_umid_keypad();
				},
				dataType: "json"
			});

		} else {
			if (manual_umid_timeout >= 0) {
				clearTimeout(manual_umid_timeout);
			}
			if (manual_umid_enter.length) {
				// Want to clear things if someone gets halfway through and quits.
				// Wait 15 seconds.
				manual_umid_timeout = setTimeout(clear_umid_keypad, 15000);
			}
		}
	}
});

function clear_umid_keypad () {
	manual_umid_enter = '';
	$("#keypad-umid-status").effect("shake");
	$("#keypad-umid-status block").removeClass("umid-status-blue");
}

$(".btn-trans-showhide").click(function () {
	var transaction_id = $(this).attr("id").split("-")[2];
	var transaction = $("#transaction-"+transaction_id)

	if (transaction.is(":visible")) {
		transaction.hide();
		$("#transaction-small-tohide-"+transaction_id).hide();
		$("#transaction-small-toshow-"+transaction_id).show();
	} else {
		transaction.show();
		$("#transaction-small-tohide-"+transaction_id).show();
		$("#transaction-small-toshow-"+transaction_id).hide();
	}
});

$(".faq-q").click(function() {
	$(this).next().toggle("fast");
});


//
// Pools
//




if (onscreen_keyboard) {
	$(".keyboard-wanted").keyboard({
	  layout : 'qwerty',
	  tabNavigation : true,
	  enterNavigation : true,
	});
}

var scrollStep = 100;

$("#scrollTop").bind("click", function(event) {
  event.preventDefault();
  $("#scrollMe").animate({
    scrollTop: "= 0px"
  });
});
$("#scrollUp").bind("click", function(event) {
  event.preventDefault();
  $("#scrollMe").animate({
    scrollTop: "-=" + scrollStep + "px"
  });
});
$("#scrollDown").bind("click", function(event) {
  event.preventDefault();
  $("#scrollMe").animate({
    scrollTop: "+=" + scrollStep + "px"
  });
});
$("#scrollBot").bind("click", function(event) {
  event.preventDefault();
  $("#scrollMe").animate({
    scrollTop: "+=" + $("#scrollMe").height() + "px"
  });
});
