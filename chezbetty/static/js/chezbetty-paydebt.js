
// Keep a pointer to the most recent handler so we can close it
var active_handler = undefined;

// On "Pay Debt" button click
$('.btn-paydebt').on('click', function(e) {

  // Get key properties for `data-X` attributes on the button
  var stripe_pk   = $(this).attr('data-stripepubkey');
  var uniqname    = $(this).attr('data-uniqname');
  var amount      = $(this).attr('data-amount');
  var total_cents = $(this).attr('data-total-cents');
  var image_url   = $(this).attr('data-imageurl');

  // Setup data struct for skype
  var handler = StripeCheckout.configure({
    key: stripe_pk,
    image: image_url,
    token: function(token) {
      console.log(token);
      // Callback w/ token.id to create a charge and token.email
      $.ajax({
        type: 'POST',
        url: '/paydebt/' + uniqname + '/submit',
        data: {
          stripeToken: token.id,
          betty_amount: amount,
          betty_total_cents: total_cents
        },
        success: function () {
          window.location.reload();
        },
        error: function (e) {
          console.log(e);
          alert("Error posting data to server");
        },
        dataType: "json"
      });
    },
    name: 'Chez Betty',
    description: '$' + parseFloat(amount).toFixed(2) + ' Deposit ($' + (total_cents/100).toFixed(2) + ' Charge)',
    amount:  total_cents ,
  });

  // Show the pay popup
  handler.open();
  active_handler = handler;

  e.preventDefault();
});

$(window).on('popstate', function() {
  if (active_handler != undefined) {
    active_handler.close();
  }
});
