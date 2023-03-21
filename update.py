import base64
import json
import logging
from datetime import datetime
import os

import requests

from tqdm import tqdm
from typeform import Typeform
from shopify_uploader import ShopifyUploader
from typeform_handler import TypeformHandler

from swap_product import SwapProduct

# API_KEY = '386fc2affdf916b1166de44507f010a1'
# PASSWORD = 'science'
# API_SECRET = '545b34fe770840329eff189243499c32'
# Before using with a new shop, set a proper location id.
# Find it manually with
# session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
# shopify.Location.activate_session(session)
# locations = shopify.Location.find()
# shopify.Location.get(id)

def setup_logging():
    logging.basicConfig(filename='logs/logs.txt', filemode='a')
    logging.root.setLevel(logging.INFO)
    logging.info(f'Typeform uploader script started at {datetime.now()}')
       
def run_update(form_type: int):
    setup_logging()
    typeformHandler = TypeformHandler(form_type) 
    responses = typeformHandler.typeform_get_responses()
    
    isP2P = form_type == TypeformHandler.USER_FORM;
    shopifyUploader = ShopifyUploader(typeformHandler)

    for response in tqdm((responses)):
        
        logging.info(f"'Parsing response submitted at {response['submitted_at']}', response token {response['token']}")
        
        
        swap_product = typeformHandler.create_swap_product_from_response(response['answers'], isP2P)
        shopifyUploader.upload_product(response['token'], swap_product)
    
    logging.info(f"Uploader script completed at {datetime.now()}")

"""
- background remover
    - heic to jpeg
        if response['token'] != '35b05rgs653ismib35bqyadr61bjxe0g': continue
    - crop white space after background removal
        (need to preserve relative image size),
        crop front/back by least size allowed by front/back picture
        crop size/brand independently

- Do not upload same typeform images

- discriminate by email moderator/swapper
- coin calulator: 1.2 for material everywhere
- swapper: customer id, find by emial
- weight: average


- photos allowed (for Shopify) .png, .gif or .jpg (.jpeg works) (me??)

Future:
- email / whatapp
- instagram stories
"""
