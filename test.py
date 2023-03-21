import json
import os
from typeform_handler import TypeformHandler
from shopify_uploader import ShopifyUploader
import shopify

SHOP_URL =  'dont-shop-swap.myshopify.com'
ACCESS_TOKEN = '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'
API_VERSION = '2022-10'

def pp(json_str):
    json.dumps(json_str, indent=4)

def test():
    
    open('.TEST', 'w').close()

    typeformHandler = TypeformHandler(form_type) 
    responses = typeformHandler.typeform_get_responses()
    print((responses[0]))
    # print(len(responses))
    exit(0)
    #os.unlink('.TEST')

    with shopify.Session.temp(SHOP_URL, API_VERSION, ACCESS_TOKEN):
        user = shopify.Customer.search(query='email:akhil.hardys@gmail.com', fields='id, first_name, last_name')
        print(user[0].id)
            

form_type = TypeformHandler.USER_FORM
test()
