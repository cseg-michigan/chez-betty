
import urllib
import time
import json
import hashlib
import hmac


class BTCException(Exception):
    pass

class Bitcoin(object):

    COINBASE_API_KEY = ""
    COINBASE_API_SECRET = ""

    def __init__(self, umid=None):
        self.umid = umid
        pass

    def req(self, url, body=None):
        opener = urllib.request.build_opener()
        nonce = int(time.time() * 1e6)
        message = str(nonce) + url + ('' if body is None else body)
        signature = hmac.new(bytes(self.COINBASE_API_SECRET, "utf-8"), bytes(message, "utf-8"), hashlib.sha256).hexdigest()
        opener.addheaders = [('ACCESS_KEY', self.COINBASE_API_KEY),
                             ('ACCESS_SIGNATURE', signature),
                             ('ACCESS_NONCE', nonce)]
        return opener.open(urllib.request.Request(url, bytes(body, "utf-8"), {'Content-Type': 'application/json'}))


    def get_new_address(self, cb_url='http://chezbetty.zakird.com/bitcoin/deposit', guid='chezbetty'):
        try:
            opener = self.req("https://coinbase.com/api/v1/account/generate_receive_address",
                 '{"address": {"callback_url": "%s/%s", "label": "%s"}' % (cb_url, self.umid, guid))
        except urllib.error.HTTPError as e:
            raise BTCException("Could not get address")

        res = opener.read()
        obj = json.loads(str(res, 'utf-8'))

        if not(obj['success']):
            raise BTCException("Could not get address: %s" % res)

        return obj['address']

