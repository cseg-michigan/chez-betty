# Generates dynamic file content on the fly from the DB

from pyramid.events import subscriber
from pyramid.events import BeforeRender
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render
from pyramid.renderers import render_to_response
from pyramid.response import Response
from pyramid.response import FileResponse, FileIter
from pyramid.view import view_config, forbidden_view_config

from .models import *
from .models.model import *
from .models import user as __user
from .models.user import User
from .models.item import Item
from .models.box import Box
from .models.box_item import BoxItem
from .models.transaction import Transaction, Deposit, CashDeposit, BTCDeposit, Purchase
from .models.transaction import Inventory, InventoryLineItem
from .models.transaction import PurchaseLineItem, SubTransaction, SubSubTransaction
from .models.account import Account, VirtualAccount, CashAccount
from .models.event import Event
from .models import event as __event
from .models.vendor import Vendor
from .models.item_vendor import ItemVendor
from .models.box_vendor import BoxVendor
from .models.request import Request
from .models.announcement import Announcement
from .models.btcdeposit import BtcPendingDeposit
from .models.receipt import Receipt
from .models.pool import Pool
from .models.pool_user import PoolUser

@view_config(route_name='dynamic_item_img')
def dynamic_item_img(request):
	item = Item.from_id(request.matchdict['item_id'])
	response = Response(content_type='image/jpeg')
	class Hack():
		def __init__(self, img):
			self.img = img
			self.idx = 0
		def getattr(self, item):
			print("item {}".format(item))
			raise AttributeError
		def __getattr(self, item):
			print("item {}".format(item))
			raise AttributeError
		def read(self, block_size = None):
			if self.idx >= len(self.img):
				return ''
			if block_size is None:
				self.idx = len(self.img)
				return self.img
			if self.idx + block_size > len(self.img):
				r = self.img[self.idx:]
				self.idx = len(self.img)
				return r
			else:
				r = self.img[self.idx:block_size]
				self.idx += block_size
				return r
		def close(self):
			pass
	h = Hack(item.img.img)
	response.app_iter = FileIter(h)
	return response
