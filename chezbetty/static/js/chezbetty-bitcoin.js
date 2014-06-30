

function check_btc(){
    addr = $('#btcaddr').text()
    $.getJSON('/bitcoin/check/'+addr, function (obj) {
        if (obj.result != 0) {
            document.location = '/transaction/'+obj.result
        }
    });
}

setInterval(check_btc, 1500);
