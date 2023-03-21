import json
import logging
import requests
from typeform import Typeform

from swap_product import SwapProduct


class TypeformHandler:

    TEAM_FORM = 1
    USER_FORM = 2

    __TYPEFORM_TOKEN = 'tfp_Szdsy8sB4vdevcFrxbTZ3ZrnSpVnNTx2wWLGPCagJEF_3mQ2r4PUvaDeYh'
    
    def __init__(self, formType: int):
        if formType == TypeformHandler.TEAM_FORM:
            self.__config_file = 'typeform_config_team.json'
            self.__last_updated_token_file = 'last_uploaded_token.txt'
        elif formType == TypeformHandler.USER_FORM:
            self.__config_file = 'typeform_config.json'
            self.__last_updated_token_file = 'last_uploaded_token_user.txt'
        
        with open(self.__config_file) as file:
            config = json.loads(file.read())

        # forms_dict = typeform.forms.list()
        # form_id = forms_dict['items'][0]['id']
        self.__TYPEFORM_FORM_ID = config['typeform_form_id']
        # form = typeform.forms.get(form_id)

        self.__FRONT_IMAGE_FIELD_ID = config.get('front_image_question_id', None)
        self.__BACK_IMAGE_FIELD_ID = config.get('back_image_question_id', None)
        self.__SIZE_IMAGE_FIELD_ID = config.get('size_image_question_id', None)
        self.__VENDOR_IMAGE_FIELD_ID = config.get('vendor_image_question_id', None)
        self.__IMPERFECTIONS_IMAGE_FIELD_ID = config.get('imperfections_image_question_id', None)

        self.__BRAND_FIELD_ID = config.get('brand_question_id', None)
        self.__ADJECTIVE_FIELD_ID = config.get('adjective_question_id', None)
        self.__ITEM_TYPE_FIELD_ID = config.get('item_type_question_id', None)
        self.__CONDITION_FIELD_ID = config.get('condition_question_id', None)
        self.__SIZE_FIELD_ID = config.get('size_question_id', None)
        self.__ADDITIONAL_TEXT_FIELD_ID = config.get('additional_text_question_id', None)
        self.__TAGS_FIELD_ID = config.get('tags_field_id', None)

        self.__EMAIL_FIELD_ID = config.get('email_question_id', None)

    def typeform_get_responses(self, num_results: int = 1000):
        typeform = Typeform(TypeformHandler.__TYPEFORM_TOKEN)

        with open(self.__last_updated_token_file) as token_file:
            last_uploaded_token = token_file.read().strip()
        
        responses_dict = typeform.responses.list(self.__TYPEFORM_FORM_ID, pageSize=num_results, after=last_uploaded_token)
        
        if not responses_dict['items']:
            print("No new responses")
            exit(0)

        return responses_dict['items']
    
    def download_typeform_image(self, file_url) -> bytes:
        r = requests.get(file_url,headers={'Authorization': f'Bearer {TypeformHandler.__TYPEFORM_TOKEN}'})

        if r.status_code == 200:
            logging.info(f'Successfully downloaded image: {file_url}')
        else:
            logging.error(f"Typeform returned {r.status_code} when trying to download image for file_url={file_url}")
        return r.content
    
    def create_swap_product_from_response(self, answers, isp2p = False):

        image_fields = {self.__FRONT_IMAGE_FIELD_ID, self.__BACK_IMAGE_FIELD_ID, self.__SIZE_IMAGE_FIELD_ID, self.__VENDOR_IMAGE_FIELD_ID, self.__IMPERFECTIONS_IMAGE_FIELD_ID}
        
        swap_product = SwapProduct()
        
        for answer in answers:
            
            field_id = answer['field']['id']
            
            if field_id in image_fields:
                file_url = answer['file_url']
                logging.info(f'Downloading image')
                image = self.download_typeform_image(file_url)

                if field_id == self.__FRONT_IMAGE_FIELD_ID:
                    swap_product.set_front_image(image)
                elif field_id == self.__BACK_IMAGE_FIELD_ID:
                    swap_product.set_back_image(image)
                elif field_id == self.__SIZE_IMAGE_FIELD_ID:
                    swap_product.set_side_image(image)
                elif field_id == self.__VENDOR_IMAGE_FIELD_ID:
                    swap_product.set_brand_image(image)
                elif field_id == self.__IMPERFECTIONS_IMAGE_FIELD_ID:
                    swap_product.set_imperfections_image(image)

            elif field_id == self.__BRAND_FIELD_ID:
                swap_product.brand = answer['text']
            elif field_id == self.__ADJECTIVE_FIELD_ID:
                swap_product.adjective = answer['text']
            elif field_id == self.__ITEM_TYPE_FIELD_ID:
                swap_product.item_type = answer['choice']['label']
            elif field_id == self.__CONDITION_FIELD_ID:
                swap_product.condition = answer['choice']['label']
            elif field_id == self.__SIZE_FIELD_ID:
                swap_product.size = answer['choice']['label']
            elif field_id == self.__EMAIL_FIELD_ID:
                swap_product.email = answer['email']
            elif field_id == self.__ADDITIONAL_TEXT_FIELD_ID:
                swap_product.additional_text = answer['text']
                logging.info(swap_product.additional_text)
            elif field_id == self.__TAGS_FIELD_ID:
                swap_product.extra_tags = [tag.strip().lower() for tag in answer['text'].split(',')]
            else:
                if field_id == 'ff6s76tc2lzC':  # 'Want to add another item'
                    continue
                logging.error(f'Add a new field id: {field_id}, {json.dumps(answer)}')
            
            
            swap_product.set_is_p2p(isp2p)
        
        return swap_product
    

    def get_last_updated_token_file(self):
        return self.__last_updated_token_file

