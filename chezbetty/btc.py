
from .model import *
from .account import Account
from .transaction import Transaction
import urllib2


class Bitcoin(object):

    COINBASE_API_KEY = ""
    COINBASE_API_SECRET = ""

    def __init__(self):
        pass

    def req(self, data=None):
        opener = urllib2.build_opener()
        nonce = int(time.time() * 1e6)
        message = str(nonce) + url + ('' if body is None else body)
        signature = hmac.new(self.COINBASE_API_SECRET, message, hashlib.sha256).hexdigest()
        opener.addheaders = [('ACCESS_KEY', self.COINBASE_API_KEY),
                             ('ACCESS_SIGNATURE', signature),
                             ('ACCESS_NONCE', nonce)]
        try:
            return opener.open(urllib2.Request(url, body, {'Content-Type': 'application/json'}))
        except urllib2.HTTPError as e:
            # TODO: error to user? don't display address?
            print(e)
        return e


    def get_new_address(self, cb_url='http://141.212.11.139:6543/bitcoin/deposit', guid='chezbetty'):
        res = self.req("https://coinbase.com/api/v1/account/generate_receive_address",
                 '{"address": {"callback_url": "%s/%s", "label": "%s"}' % (cb_url, guid, guid))

        obj = json.loads(res)
        if not(obj['success']):
            raise Exception("Could not get address: %s" % res)

        print(req)
        return obj['address']

