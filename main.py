import base64
import json
import logging
from datetime import datetime

import requests
import shopify
from tqdm import tqdm
from typeform import Typeform

from swap_product import SwapProduct

# API_KEY = '386fc2affdf916b1166de44507f010a1'
# PASSWORD = 'science'
# API_SECRET = '545b34fe770840329eff189243499c32'

SHOP_NAME = 'dont-shop-swap'
SHOP_URL = SHOP_NAME + '.myshopify.com'
ACCESS_TOKEN = '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'
API_VERSION = '2022-10'

TYPEFORM_TOKEN = 'tfp_Szdsy8sB4vdevcFrxbTZ3ZrnSpVnNTx2wWLGPCagJEF_3mQ2r4PUvaDeYh'

# Before using with a new shop, set a proper location id.
# Find it manually with
# session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
# shopify.Location.activate_session(session)
# locations = shopify.Location.find()
# shopify.Location.get(id)

DSS_STUDIO_LOCATION_ID = 66102919352
CHOBHAM_LOCATION_ID = 60955099320
P2P_LOCATION_ID = 74125705535

with open('typeform_config_team.json') as file:
    config = json.loads(file.read())

# forms_dict = typeform.forms.list()
# form_id = forms_dict['items'][0]['id']
TYPEFORM_FORM_ID = config['typeform_form_id']

# form = typeform.forms.get(form_id)

FRONT_IMAGE_FIELD_ID = config['front_image_question_id']
BACK_IMAGE_FIELD_ID = config['back_image_question_id']
SIDE_IMAGE_FIELD_ID = config['side_image_question_id']
VENDOR_IMAGE_FIELD_ID = config['vendor_image_question_id']
IMPERFECTIONS_IMAGE_FIELD_ID = config['imperfections_image_question_id']

BRAND_FIELD_ID = config['brand_question_id']
ADJECTIVE_FIELD_ID = config['adjective_question_id']
ITEM_TYPE_FIELD_ID = config['item_type_question_id']
CONDITION_FIELD_ID = config['condition_question_id']
SIZE_FIELD_ID = config['size_question_id']
ADDITIONAL_TEXT_FIELD_ID = config['additional_text_question_id']
TAGS_FIELD_ID = config['tags_field_id']

EMAIL_FIELD_ID = config['email_question_id']


def calc_price_from_coins(coins: int):
    if coins > 1000:
        logging.warning(f'Coins > 1000 for some item, coins = {coins}')
    if coins >= 400:
        return 10
    price = coins / 50 + 2
    if price == int(price):
        return int(price)
    return price


def upload_product(token: str, product: SwapProduct, coin_price: int, price: int|float):
    # session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
    # shopify.ShopifyResource.activate_session(session)

    # TODO: canonize brand
    # TODO: support different size types
    title = ''
    if product.brand != 'Unbranded':
        title += product.brand
    title += ' ' + ' '.join(word.capitalize() for word in product.adjective.split())
    title += ' ' + product.item_type
    title += ', ' + product.get_size_for_title()
    description = product.additional_text
    if description:
        description = description[0].capitalize() + description[1:]
    if description:
        description += '<br/><br/>'
    description += f"""
    <b>Size: {product.size}</b><br/>
    <b>Condition: {product.condition}</b><br/>
    <b>Service fee: £{price}</b>
    """
    # TODO: add full text when coin calculator is figured out
    # <b>This product is worth {coin_price} swap coins and has a £{price} service fee.</b>

    if product.is_p2p():
        if description:
            description += '<br/><br/>'
        description += 'This item has been remotely uploaded by another swapper, ' \
                       'it may arrive separately from the rest of your order.'
    tags = product.get_tags()

    images = []
    for image_bytes in product.get_all_images():
        images.append({'attachment': base64.b64encode(image_bytes).decode('ascii')})

    arguments = {
        'size': product.size,
        'title': title,
        'body_html': description,
        'vendor': product.brand,
        'product_type': product.item_type,
        'tags': tags,
        'status': 'draft',
        'variants': [  # TODO(me)
            {
                'weight': product.get_weight(),
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

    is_p2p = product.is_p2p()

    with shopify.Session.temp(SHOP_URL, API_VERSION, ACCESS_TOKEN):
        # Create product.
        product = shopify.Product.create(arguments)
        if product.errors.errors is None:
            logging.error(f'Product not created: {title}, {product}')
            print(product.errors.errors)
            return

        logging.info(f'Product created: ID={product.id}, {title}')

        # Add inventory.
        # https://shopify.dev/api/admin-rest/2023-01/resources/inventorylevel#post-inventory-levels-adjust
        inventory_item_id = product.variants[0].inventory_item_id
        inventory_level = shopify.InventoryLevel.set(P2P_LOCATION_ID if is_p2p else DSS_STUDIO_LOCATION_ID,
                                                     inventory_item_id, 1)

        if inventory_level.errors.errors:
            logging.error(f'Error when adding inventory level: {inventory_level.errors.errors}')
        else:
            logging.info(f'Added inventory +1: ID={product.id}')
            with open('last_uploaded_token.txt', 'w') as file:
                file.write(token)

        # Add metafields.
        coin_price_metafield = shopify.Metafield.create(
            {'namespace': 'global', 'key': 'coin_price', 'value': coin_price,
             'type': 'number_integer', 'owner_id': product.id, 'owner_resource': 'product'})

        coin_price_type_metafield = shopify.Metafield.create(
            {'namespace': 'global', 'key': 'coin_price_type', 'value': 'purple',
             'type': 'single_line_text_field', 'owner_id': product.id, 'owner_resource': 'product'})

        peer_to_peer_metafield = shopify.Metafield.create(
            {'namespace': 'custom', 'key': 'peer_to_peer', 'value': is_p2p,
             'type': 'boolean', 'owner_id': product.id, 'owner_resource': 'product'})

        if coin_price_metafield.errors.errors or coin_price_type_metafield.errors.errors \
                or peer_to_peer_metafield.errors.errors:
            logging.info(f'Metafield creation errors: {coin_price_metafield.errors.errors}, '
                         f'\n{coin_price_type_metafield.errors.errors},'
                         f'\n{peer_to_peer_metafield.errors.errors}')
        else:
            logging.info(f'Metafields created: {coin_price_metafield.id}, {coin_price_type_metafield.id}, '
                         f'{peer_to_peer_metafield.id}')


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

def typeform_get_responses(num_results: int = 1000):
    typeform = Typeform(TYPEFORM_TOKEN)

    with open('last_uploaded_token.txt') as token_file:
        last_uploaded_token = token_file.read().strip()
    
    responses_dict = typeform.responses.list(TYPEFORM_FORM_ID, pageSize=num_results, after= last_uploaded_token)
    return responses_dict['items']

def create_swap_product_from_response(answers):

    image_fields = {FRONT_IMAGE_FIELD_ID, BACK_IMAGE_FIELD_ID, SIDE_IMAGE_FIELD_ID, VENDOR_IMAGE_FIELD_ID, IMPERFECTIONS_IMAGE_FIELD_ID}
     
    swap_product = SwapProduct()
    
    for answer in answers:
        
        field_id = answer['field']['id']
        
        if field_id in image_fields:
            file_url = answer['file_url']
            logging.info(f'Downloading image')
            image = download_typeform_image(file_url)

            if field_id == FRONT_IMAGE_FIELD_ID:
                swap_product.set_front_image(image)
            elif field_id == BACK_IMAGE_FIELD_ID:
                swap_product.set_back_image(image)
            elif field_id == SIDE_IMAGE_FIELD_ID:
                swap_product.set_side_image(image)
            elif field_id == VENDOR_IMAGE_FIELD_ID:
                swap_product.set_brand_image(image)
            elif field_id == IMPERFECTIONS_IMAGE_FIELD_ID:
                swap_product.set_imperfections_image(image)

        elif field_id == BRAND_FIELD_ID:
            swap_product.brand = answer['text']
        elif field_id == ADJECTIVE_FIELD_ID:
            swap_product.adjective = answer['text']
        elif field_id == ITEM_TYPE_FIELD_ID:
            swap_product.item_type = answer['choice']['label']
        elif field_id == CONDITION_FIELD_ID:
            swap_product.condition = answer['choice']['label']
        elif field_id == SIZE_FIELD_ID:
            swap_product.size = answer['choice']['label']
        elif field_id == EMAIL_FIELD_ID:
            swap_product.email = answer['email']
        elif field_id == ADDITIONAL_TEXT_FIELD_ID:
            swap_product.additional_text = answer['text']
            logging.info(swap_product.additional_text)
        elif field_id == TAGS_FIELD_ID:
            swap_product.extra_tags = [tag.strip().lower() for tag in answer['text'].split(',')]
        else:
            if field_id == 'ff6s76tc2lzC':  # 'Want to add another item'
                continue
            logging.error(f'Add a new field id: {field_id}, {json.dumps(answer)}')
    
    return swap_product
    


def typeform_swap_products(num_results: int = 1000):
    typeform = Typeform(TYPEFORM_TOKEN)

    image_fields = {FRONT_IMAGE_FIELD_ID, BACK_IMAGE_FIELD_ID, SIDE_IMAGE_FIELD_ID, VENDOR_IMAGE_FIELD_ID, IMPERFECTIONS_IMAGE_FIELD_ID}

    with open('last_uploaded_token.txt') as token_file:
        last_uploaded_token = token_file.read().strip()

    responses_dict = typeform.responses.list(TYPEFORM_FORM_ID, pageSize=num_results, since='2023-02-28T16:38:31Z')
    # TODO: make sure responses are sorted from past to future,
    #  so that uploads to Shopify preserve the chronological order
    # typeform DOES NOT guarantee this to be sorted, and I did catch problems here

    # TODO: tqdm is a bit wonky and one-off because it's inside a generator
    for response in tqdm(list(reversed(responses_dict['items']))):
        logging.info(f"'Parsing response submitted at {response['submitted_at']}', response token {response['token']}")
        swap_product = SwapProduct()
        for answer in response['answers']:
            field_id = answer['field']['id']
            if field_id in image_fields:
                file_url = answer['file_url']
                logging.info(f'Downloading image')
                image = download_typeform_image(file_url)

                if field_id == FRONT_IMAGE_FIELD_ID:
                    swap_product.set_front_image(image)
                elif field_id == BACK_IMAGE_FIELD_ID:
                    swap_product.set_back_image(image)
                elif field_id == SIDE_IMAGE_FIELD_ID:
                    swap_product.set_side_image(image)
                elif field_id == VENDOR_IMAGE_FIELD_ID:
                    swap_product.set_brand_image(image)
                elif field_id == IMPERFECTIONS_IMAGE_FIELD_ID:
                    swap_product.set_imperfections_image(image)

            elif field_id == BRAND_FIELD_ID:
                swap_product.brand = answer['text']
            elif field_id == ADJECTIVE_FIELD_ID:
                swap_product.adjective = answer['text']
            elif field_id == ITEM_TYPE_FIELD_ID:
                swap_product.item_type = answer['choice']['label']
            elif field_id == CONDITION_FIELD_ID:
                swap_product.condition = answer['choice']['label']
            elif field_id == SIZE_FIELD_ID:
                swap_product.size = answer['choice']['label']
            elif field_id == EMAIL_FIELD_ID:
                swap_product.email = answer['email']
            elif field_id == ADDITIONAL_TEXT_FIELD_ID:
                swap_product.additional_text = answer['text']
                logging.info(swap_product.additional_text)
            elif field_id == TAGS_FIELD_ID:
                swap_product.extra_tags = [tag.strip().lower() for tag in answer['text'].split(',')]
            else:
                if field_id == 'ff6s76tc2lzC':  # 'Want to add another item'
                    continue
                logging.error(f'Add a new field id: {field_id}, {json.dumps(answer)}')

        yield response['token'], swap_product

def main():
    logging.basicConfig(filename='logs/logs.txt', filemode='a')
    logging.root.setLevel(logging.INFO)
    logging.info(f'Typeform uploader script started at {datetime.now()}')

    responses = typeform_get_responses()
    if not responses:
        print("No new responses")
        exit(0)

    for response in tqdm((responses)):
        
        logging.info(f"'Parsing response submitted at {response['submitted_at']}', response token {response['token']}")
        swap_product = create_swap_product_from_response(response['answers'])

        # coin_price = calc_coin_price(brand, item_type)
        coin_price = 50
        price = calc_price_from_coins(coin_price)
        
        upload_product(response['token'], swap_product, coin_price, price)
    
    logging.info(f"Uploader script completed at {datetime.now()}")

if __name__ == '__main__':
    main()

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
