import base64
import logging
import shopify
from typeform_handler import TypeformHandler
from swap_product import SwapProduct


class ShopifyUploader:

    
    __SHOP_NAME = 'dont-shop-swap'
    __SHOP_URL =  'dont-shop-swap.myshopify.com'
    __ACCESS_TOKEN = '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'
    __API_VERSION = '2022-10'
    __DSS_STUDIO_LOCATION_ID = 66102919352
    __CHOBHAM_LOCATION_ID = 60955099320
    __P2P_LOCATION_ID = 74125705535
    
    def __init__(self, typeFormHandler: TypeformHandler):
        self.typeFormHandler = typeFormHandler

    def upload_product(self, token: str, product: SwapProduct):
        # session = shopify.Session(SHOP_URL, API_VERSION, ACCESS_TOKEN)
        # shopify.ShopifyResource.activate_session(session)

        # TODO: canonize brand
        # TODO: support different size types

         # coin_price = calc_coin_price(brand, item_type)

        coin_price = 50
        price = self.calc_price_from_coins(coin_price)

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
        owner_email = product.email or 'x'

        with shopify.Session.temp(ShopifyUploader.__SHOP_URL, ShopifyUploader.__API_VERSION, ShopifyUploader.__ACCESS_TOKEN):
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
            inventory_level = shopify.InventoryLevel.set(ShopifyUploader.__P2P_LOCATION_ID if is_p2p else ShopifyUploader.__DSS_STUDIO_LOCATION_ID,
                                                        inventory_item_id, 1)

            if inventory_level.errors.errors:
                logging.error(f'Error when adding inventory level: {inventory_level.errors.errors}')
            else:
                logging.info(f'Added inventory +1: ID={product.id}')
                with open(self.typeFormHandler.get_last_updated_token_file(), 'w') as file:
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
            
            if (is_p2p):

                owner = shopify.Customer.search(query=f'email:{owner_email}', fields='id, first_name, last_name')
                if (not owner):
                    f = open('no_account_found.txt', 'w')
                    f.write(owner_email)
                    logging.error(f'Owner with {owner_email} not found.')
                else:
                    owner = owner[0]
                    owner_customer_id = shopify.Metafield.create(
                    {'namespace': 'custom', 'key': 'customer_id', 'value': owner.id,
                    'type': 'number_integer', 'owner_id': product.id, 'owner_resource': 'product'})

                    owner_customer_name = shopify.Metafield.create(
                    {'namespace': 'custom', 'key': 'customer_name', 'value': f'{owner.first_name} {owner.last_name}',
                    'type': 'single_line_text_field', 'owner_id': product.id, 'owner_resource': 'product'})

                    owner_peer_to_peer_metafield = shopify.Metafield.create(
                    {'namespace': 'custom', 'key': 'peer_to_peer_customer', 'value': True,
                    'type': 'boolean', 'owner_id': owner.id, 'owner_resource': 'customer'})

                    if owner_customer_id.errors.errors or owner_customer_name.errors.errors or owner_peer_to_peer_metafield:
                        logging.info(f'Metafield creation errors: {owner_customer_id.errors.errors}, '
                            f'\n{owner_customer_name.errors.errors}, {owner_peer_to_peer_metafield}')
                    else:
                        logging.info(f'Metafields created: {owner_customer_id.id}, {owner_customer_name.id}, {owner_peer_to_peer_metafield}')

    def calc_price_from_coins(self, coins: int):
        if coins > 1000:
            logging.warning(f'Coins > 1000 for some item, coins = {coins}')
        if coins >= 400:
            return 10
        price = coins / 50 + 2
        if price == int(price):
            return int(price)
        return price

