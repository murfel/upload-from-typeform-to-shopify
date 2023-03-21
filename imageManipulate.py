import os
from rembg import remove
import io
import logging
import PIL
from PIL import Image, ExifTags

import PIL
import requests
from PIL import Image

REMOVE_BG_TOKEN = 'Q1opKLc9VgX59WX8WbF7ztjf'

def remove_background(image: bytes) -> bytes:
    is_test = os.path.exists('.TEST')

    if (is_test):
        print(f"IS_TEST IS {is_test}")
        return image  # saving quota

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

# def remove_background(image: bytes) -> bytes:

#     input = Image.open(io.BytesIO(image))
#     output = remove(input)

#     #correct orientation in case it's changed
#     orientation = 274
#     for key in ExifTags.TAGS.keys():
#         if ExifTags.TAGS[key]=='Orientation':
#             orientation = key
#             break
        
#     exif = input.getexif()

#     if exif[orientation] == 3:
#         output=output.rotate(180, expand=True)
#     elif exif[orientation] == 6:
#         output=output.rotate(270, expand=True)
#     elif exif[orientation] == 8:
#         output=output.rotate(90, expand=True)

#     buffer = io.BytesIO()
#     output.save(buffer, format='PNG', optimize=True)
#     logging.info(f'Successfully removed background')


#     return buffer.getvalue()



def crop(image_data: bytes, preview=False) -> bytes:
    if not image_data:
        logging.error('Trying to crop empty image')
    try:
        image = Image.open(io.BytesIO(image_data))
    except PIL.UnidentifiedImageError:
        logging.warning("Couldn't crop: PIL.UnidentifiedImageError")
        return image_data
    width, height = image.size
    new_size = (400, 650) if preview else (1600, 2000)
    if width > height:
        new_size = new_size[1], new_size[0]
    image.thumbnail(new_size)
    exif = image.info['exif'] if 'exif' in image.info else None
    byte_array = io.BytesIO()
    if exif:
        image.save(byte_array, format=image.format, exif=exif)
    else:
        image.save(byte_array, format=image.format)
    logging.info(f'Successfully cropped, image format: {image.format}')
    return byte_array.getvalue()

