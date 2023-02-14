import base64
import json
import logging
from typing import List

import requests
import shopify
from tqdm import tqdm
from typeform import Typeform

from swap_product import SwapProduct

# API_KEY = '386fc2affdf916b1166de44507f010a1'
# PASSWORD = 'science'
# API_SECRET = '545b34fe770840329eff189243499c32'

SHOP_NAME = 'rocket-science-biz-development'
SHOP_URL = SHOP_NAME + '.myshopify.com'
ACCESS_TOKEN = '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'
API_VERSION = '2022-10'

TYPEFORM_TOKEN = 'tfp_Szdsy8sB4vdevcFrxbTZ3ZrnSpVnNTx2wWLGPCagJEF_3mQ2r4PUvaDeYh'

# TODO: before using with a new shop, set a proper location id.
# Find it manually with
# locations = shopify.Location.find()
LOCATION_ID = 78160462144

with open('typeform_config.json') as file:
    config = json.loads(file.read())

# forms_dict = typeform.forms.list()
# form_id = forms_dict['items'][0]['id']
TYPEFORM_FORM_ID = config['typeform_form_id']

# form = typeform.forms.get(form_id)

FRONT_IMAGE_FIELD_ID = config['front_image_question_id']
BACK_IMAGE_FIELD_ID = config['back_image_question_id']
SIZE_IMAGE_FIELD_ID = config['size_image_question_id']
VENDOR_IMAGE_FIELD_ID = config['vendor_image_question_id']
ADDITIONAL_TEXT_FIELD_ID = config['additional_text_question_id']
EMAIL_FIELD_ID = config['email_question_id']


def calc_price_from_coins(coins: int):
    if coins > 1000:
        logging.warning(f'Coins > 1000 for some item, coins = {coins}')
    if coins >= 400:
        return 10
    return coins / 50 + 2


def get_coin_price_type(coins: int):
    return 'purple'  # TODO: ask Lydia


def upload_product(brand, colour, pattern, item_type, size, description, coin_price: int,
                   images_bytes_list: List[bytes], remote_swapper=True):
    # session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    # shopify.ShopifyResource.activate_session(session)

    # brand is not capitalized on purpose
    colour.capitalize()
    pattern.capitalize()
    item_type.capitalize()
    size.capitalize()

    coin_price_type = get_coin_price_type(coin_price)
    price = calc_price_from_coins(coin_price)
    title = f'{brand} {colour} {pattern} {item_type}, {size}'
    if remote_swapper:
        if description:
            description += '<br/><br/>'
        description += 'This item has been remotely uploaded by another swapper, ' \
                       'it may arrive separately from the rest of your order.'
    tags = ', '.join(
        [brand, colour, item_type, size[len('Size '):]] + ['p2p'] if remote_swapper else [])  # TODO: ask Lydia

    images = []
    for image_bytes in images_bytes_list:
        images.append({'attachment': base64.b64encode(image_bytes).decode('ascii')})

    arguments = {
        'brand ': brand,
        'colour': colour,
        'pattern': pattern,
        'item': item_type,
        'size': size,
        'title': title,
        'body_html': description,
        'vendor': brand,
        # 'type': item_type,
        'product_type': item_type,
        'tags': tags,
        'status': 'active',
        'coin_price': coin_price,
        # 'coin_price_type': coin_price_type,  # TODO: Lydia
        'variants': [  # TODO(me)
            {
                'weight': 0.1,  # TODO: ask Lydia
                'weight_unit': 'lb',
                'price': price,
                'taxable': True,
                'inventory_management': 'shopify',
                'fulfillment_service': 'manual',
                'requires_shipping': True,
                'inventory_quantity': 1
            }
        ],
        'images': images
    }

    with shopify.Session.temp(SHOP_URL, API_VERSION, ACCESS_TOKEN):
        product = shopify.Product.create(arguments)
        if product.errors.errors is None:
            logging.error(f'Product not created: {title}, {product}')
            print(product.errors.errors)
        else:
            logging.info(f'Product created: ID={product.id}, {title}')

            # https://shopify.dev/api/admin-rest/2023-01/resources/inventorylevel#post-inventory-levels-adjust
            inventory_item_id = product.variants[0].inventory_item_id
            inventory_level = shopify.InventoryLevel.set(LOCATION_ID, inventory_item_id, 1)

            if inventory_level.errors.errors:
                logging.error(f'Error when adding inventory level: {inventory_level.errors.errors}')
            else:
                logging.info(f'Added inventory +1: ID={product.id}')


def pp(json_str):
    json.dumps(json_str, indent=4)


def download_typeform_image(file_url) -> bytes:
    r = requests.get(file_url,
                     headers={'Authorization': f'Bearer {TYPEFORM_TOKEN}'})

    if r.status_code == 200:
        logging.info(f'Successfully downloaded image: {file_url}')
    else:
        logging.error(f"Typeform returned {r.status_code} when trying to download image for file_url={file_url}")
    return r.content


def typeform_swap_products(num_results: int, since='2023-02-02T18:04:07Z'):
    typeform = Typeform(TYPEFORM_TOKEN)

    image_fields = {FRONT_IMAGE_FIELD_ID, BACK_IMAGE_FIELD_ID, SIZE_IMAGE_FIELD_ID, VENDOR_IMAGE_FIELD_ID}

    responses_dict = typeform.responses.list(TYPEFORM_FORM_ID, pageSize=num_results, since=since)
    for response in responses_dict['items']:
        logging.info(f"'Parsing response submitted at {response['submitted_at']}', response token {response['token']}")
        swap_product = SwapProduct()
        for answer in tqdm(response['answers']):
            field_id = answer['field']['id']
            if field_id in image_fields:
                file_url = answer['file_url']
                logging.info(f'Downloading image')
                image = download_typeform_image(file_url)

                if field_id == FRONT_IMAGE_FIELD_ID:
                    swap_product.set_front_image(image)
                elif field_id == BACK_IMAGE_FIELD_ID:
                    swap_product.set_back_image(image)
                elif field_id == SIZE_IMAGE_FIELD_ID:
                    swap_product.set_size_image(image)
                elif field_id == VENDOR_IMAGE_FIELD_ID:
                    swap_product.set_brand_image(image)

            elif field_id == EMAIL_FIELD_ID:
                swap_product.email = answer['email']
            elif field_id == ADDITIONAL_TEXT_FIELD_ID:
                swap_product.additional_text = answer['text']
                logging.info(swap_product.additional_text)
            else:
                logging.error(f'Add a new field id: {field_id}, {json.dumps(answer)}')

        yield swap_product


def main():
    logging.basicConfig()
    logging.root.setLevel(logging.INFO)
    logging.info('Typeform uploader script started')

    for product in typeform_swap_products(20):
        brand = 'DKNY'
        colour = 'Blue'
        pattern = 'Checkered'
        item_type = 'Dress'
        size = 'Size XS'
        coin_price = 100

        image_list = product.get_all_images()

        upload_product(brand, colour, pattern, item_type, size, product.additional_text, coin_price,
                       image_list)


if __name__ == '__main__':
    main()

"""
- background remover
    - heic to jpeg
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
