import logging
from typing import Optional, List, Set
from imageManipulate import remove_background, crop

class SwapProduct:
    ITEM_TYPE_TO_WEIGHT = {  # in lb
        'top': .5,
        't-shirt': .5,
        'shorts': .5,
        'skirt': .5,

        'dress': .8,
        'jumper': .8,
        'sweatshirt': .8,
        'hoodie': .8,
        'jeans': .8,
        'trousers': .8,
        'co-ord': .8,

        'dungarees': 1,

        'jacket': 1.2,

        'coat': 2,
    }

    DEFAULT_WEIGHT = .8

    def __init__(self):
        self._added_originals: Set[bytes] = set()
        self._front_image: Optional[bytes] = None
        self._back_image: Optional[bytes] = None
        self._size_image: Optional[bytes] = None
        self._brand_image: Optional[bytes] = None
        self._imperfections_image: Optional[bytes] = None

        self.brand = 'Unbranded'
        self.adjective = ''
        self.item_type = ''
        self.condition = ''
        self.size = ''
        self.extra_tags: List[str] = []

        self.email: Optional[str] = None
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

    def set_side_image(self, image: bytes):
        self._size_image = self._set_image(image)

    def set_brand_image(self, image: bytes):
        self._brand_image = crop(image)

    def set_imperfections_image(self, image: bytes):
        self._imperfections_image = self._set_image(image)

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
        if self._imperfections_image:
            images.append(self._imperfections_image)
        return images

    def is_p2p(self) -> bool:
        return False
        return bool(self.email)

    def get_weight(self):
        weight_lb = SwapProduct.DEFAULT_WEIGHT
        if self.item_type.lower() in SwapProduct.ITEM_TYPE_TO_WEIGHT.keys():
            weight_lb = SwapProduct.ITEM_TYPE_TO_WEIGHT[self.item_type.lower()]
        else:
            logging.error(f'No weight for item type: {self.item_type.lower()}, '
                          f'using default: {SwapProduct.DEFAULT_WEIGHT} lb')
        return weight_lb

    def get_size_for_title(self):
        if '=' not in self.size:
            return 'One Size'
        return 'Size ' + self.size.split(' =')[0]  # XS = UK 6-8

    def get_tags(self) -> str:

        item_type = self.item_type
        if item_type.lower() in ['hat', 'belt', 'scarf', 'bag']:
            item_type = 'Accessories'

        size_letters = ''
        if '=' not in self.size:
            size_letters = 'One Size'
        else:
            size_letters = self.size.split(' =')[0]  # XS = UK 6-8

        return ', '.join(
            ['all', self.brand.lower(), item_type.lower(), size_letters] + self.extra_tags +
            (['p2p'] if self.is_p2p() else []))
