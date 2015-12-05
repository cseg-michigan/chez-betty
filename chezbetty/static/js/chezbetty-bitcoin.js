

function check_btc(){
    addr = $('#btcaddr').text();
    $.getJSON('/terminal/bitcoin/check/'+addr, function (data) {
        if ("event_id" in data) {
            document.location = '/terminal/event/'+data.event_id;
        }
    });
}

// Periodically check to see if we have received any bitcoin
// from coinbase and if so redirect to the deposit event page
setInterval(check_btc, 1500);
