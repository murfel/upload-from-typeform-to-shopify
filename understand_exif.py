import io

from swap_product import crop, remove_background

from PIL.ExifTags import TAGS
from PIL import Image


def get_exif(image_bytes: bytes):
    pil_image = Image.open(io.BytesIO(image_bytes))
    exif = pil_image.getexif()
    print(exif)
    for key, value in exif.items():
        print(f'{TAGS[key]}: {value}')


with open('red.jpeg', 'rb') as file:
    image_bytes = file.read()
print('original')

get_exif(image_bytes)

image_bytes = crop(image_bytes)
print('after crop')

get_exif(image_bytes)

with open('red_cropped.jpeg', 'wb') as file:
    file.write(image_bytes)

removed = remove_background(image_bytes)

print('after')
get_exif(removed)

with open('red_removed.jpeg', 'wb') as file:
    file.write(removed)