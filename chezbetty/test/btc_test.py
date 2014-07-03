import requests
import json

j = {'address': '19Q7Ew6aFkYYoYGrk8czrNHmr1vUAVmxqc',
     'amount' : 1.0,
     'transaction': {'id': '342',
                     'created_at': 'fdsaf',
                     'hash': 'fdsafffdsab3434'

     }}

h = {'content-type': 'application/json'}

r = requests.post("http://memristor-v1.eecs.umich.edu:6543/bitcoin/deposit/11519022",
	data=json.dumps(j),
	headers=h)