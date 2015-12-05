
import urllib
import urllib.error
import urllib.request
import time
import json
import hashlib
import hmac
from decimal import Decimal


class BTCException(Exception):
    pass

class Bitcoin(object):

    COINBASE_API_KEY = ""
    COINBASE_API_SECRET = ""

    HOSTNAME = ''

    def __init__(self, umid=None):
        self.umid = umid
        pass

    @staticmethod
    def req(url, body=None):
        try:
            opener = urllib.request.build_opener()
            nonce = int(time.time() * 1e6)
            message = str(nonce) + url + ('' if body is None else body)
            signature = hmac.new(bytes(Bitcoin.COINBASE_API_SECRET, "utf-8"),
                                 bytes(message, "utf-8"),
                                 hashlib.sha256).hexdigest()
            opener.addheaders = [('ACCESS_KEY', Bitcoin.COINBASE_API_KEY),
                                ('ACCESS_SIGNATURE', signature),
                                ('ACCESS_NONCE', nonce)]

            # is this really how you do this in this language?
            body_b = None
            if body is not None:
                body_b = bytes(body, "utf-8")

            res_s = opener.open(urllib.request.Request(url,
                body_b, {'Content-Type': 'application/json'})).read()
            return json.loads(str(res_s, 'utf-8'))

        except urllib.error.HTTPError as e:
            raise BTCException("Could not load HTTP url %s: %s, %s" % (url, str(e), e.read()))
        except urllib.error.URLError as e:
            raise BTCException("General urllib failure: %s" % (str(e)))


    @staticmethod
    def noauth_req(url):
        try:
            opener = urllib.request.build_opener()
            res_s = opener.open(urllib.request.Request(url,
                None, {'Content-Type': 'application/json'})).read()
            return json.loads(str(res_s, 'utf-8'))
        except urllib.error.HTTPError as e:
            raise BTCException("Could not load HTTP")
        except urllib.error.URLError as e:
            raise BTCException("General urllib failure")

    @staticmethod
    def get_new_address(umid, auth_key, cb_url='{}/terminal/bitcoin/deposit'):

        cb_url = cb_url.format(Bitcoin.HOSTNAME)

        obj = Bitcoin.req("https://api.coinbase.com/v1/addresses",
                      '{"address": {"callback_url": "%s/%s/%s", "label": "%s"}}' % (cb_url, umid, auth_key, umid))

        if not(obj['success']):
            raise BTCException("Could not get address: %s" % umid)

        return obj['address']

    @staticmethod
    def get_spot_price(currency="USD"):
        obj = Bitcoin.req("https://coinbase.com/api/v1/prices/spot_rate?currency=%s" % currency)
        return Decimal(obj['amount'])

    @staticmethod
    def get_balance():
        obj = Bitcoin.req("https://coinbase.com/api/v1/account/balance")
        return Decimal(obj['amount'])

    @staticmethod
    def get_tx_by_hash(txid):
        return Bitcoin.noauth_req("https://blockchain.info/rawtx/%s" % txid)

    @staticmethod
    def get_block_height():
        return Bitcoin.noauth_req("https://blockchain.info/latestblock")["height"]

    # | separated list (e.g. "14YD3or6jXZowg8PV5VfZo9jmer8TQZHFg|1AZiKMapdu2KibenF67FHFgNbxL9sG2jt5")
    @staticmethod
    def get_tx_from_addrs(addrs):
        return Bitcoin.noauth_req("https://blockchain.info/multiaddr?active=%s" % addrs )

    @staticmethod
    def convert(amount):
        obj = Bitcoin.req("https://coinbase.com/api/v1/sells",
                          '{"qty": %s}' % (amount))

        if not(obj['success']):
            raise BTCException("failure on BTC convert (%s)" % obj['errors'])

        return Decimal(obj['transfer']['total']['amount'])

    @staticmethod
    # Returns the amount in USD that the bitcoins were exchanged for
    def convert_all():
        return Bitcoin.get_balance()*Bitcoin.get_spot_price()*Decimal(0.99)
        #raise NotImplementedError()

