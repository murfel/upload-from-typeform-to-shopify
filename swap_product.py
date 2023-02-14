import io
import logging
from typing import Optional, List, Set

import PIL
import requests
from PIL import Image

REMOVE_BG_TOKEN = 'piFNEtB5QDWAcUt7hEFmmpBS'


def crop(image_data: bytes) -> bytes:
    if not image_data:
        logging.error('Trying to crop empty image')
    try:
        image = Image.open(io.BytesIO(image_data))
    except PIL.UnidentifiedImageError:
        logging.warning("Couldn't crop: PIL.UnidentifiedImageError")
        return image_data
    width, height = image.size
    if width < height:
        new_size = 400, 650
    else:
        new_size = 650, 400
    image.thumbnail(new_size)
    exif = image.info['exif'] if 'exif' in image.info else None
    byte_array = io.BytesIO()
    if exif:
        image.save(byte_array, format=image.format, exif=exif)
    else:
        image.save(byte_array, format=image.format)
    logging.info(f'Successfully cropped, image format: {image.format}')
    return byte_array.getvalue()


def remove_background(image: bytes) -> bytes:
    # NB: removes EXIF tags and other image meta-data
    response = requests.post(
        'https://api.remove.bg/v1.0/removebg',
        files={'image_file': io.BytesIO(image)},
        data={'size': 'auto'},
        headers={'X-Api-Key': REMOVE_BG_TOKEN},
    )
    if response.status_code == requests.codes.ok:
        logging.info(f'Successfully removed background')
        return response.content
    else:
        logging.error(f"Remove background error: {response.status_code}, {response.text}")
        return image


class SwapProduct:
    def __init__(self):
        self._added_originals: Set[bytes] = set()
        self._front_image: Optional[bytes] = None
        self._back_image: Optional[bytes] = None
        self._size_image: Optional[bytes] = None
        self._brand_image: Optional[bytes] = None

        self.email: str = ''
        self.additional_text: str = ''

    def _set_image(self, image: bytes) -> Optional[bytes]:
        # de-duplicated
        if image in self._added_originals:
            return None
        self._added_originals.add(image)
        image = crop(image)
        image = remove_background(image)
        return image

    def set_front_image(self, image: bytes):
        self._front_image = self._set_image(image)

    def set_back_image(self, image: bytes):
        self._back_image = self._set_image(image)

    def set_size_image(self, image: bytes):
        self._size_image = self._set_image(image)

    def set_brand_image(self, image: bytes):
        self._brand_image = self._set_image(image)

    def get_all_images(self) -> List[bytes]:
        images = []
        if self._front_image:
            images.append(self._front_image)
        if self._back_image:
            images.append(self._back_image)
        if self._size_image:
            images.append(self._size_image)
        if self._brand_image:
            images.append(self._brand_image)
        return images
