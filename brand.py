from collections import defaultdict


def reduce_brand(brand: str) -> str:
    brand = brand.lower()
    brand = brand.strip()
    brand = ''.join(character for character in brand if character.isalpha())
    return brand


REDUCED_BRAND_TO_CANONICAL_SPELLING = {}
UNKNOWN_BRAND_VALUE = 10
REDUCED_BRAND_TO_VALUE = defaultdict(lambda: UNKNOWN_BRAND_VALUE)
with open('brand_value.csv') as file:
    for line in file:
        brand, value = line.split(',')
        reduced_brand = reduce_brand(brand)

        if reduced_brand in REDUCED_BRAND_TO_VALUE.keys():
            print(f'ERROR: brand {brand} is met multiple times in brand_value.csv')
            continue

        if reduced_brand in REDUCED_BRAND_TO_CANONICAL_SPELLING.keys():
            print(f'ERROR: reduction of brand {brand} to {reduced_brand} is colliding with another brand')
            continue

        REDUCED_BRAND_TO_CANONICAL_SPELLING[reduced_brand] = brand

        REDUCED_BRAND_TO_VALUE[reduced_brand] = int(value)


ITEM_TYPE_TO_VALUE = {

}


def calc_coin_price(brand, item_type):
    if item_type not in ITEM_TYPE_TO_VALUE.keys():
        print(f'ERROR: item type: {item_type} not in ITEM_TYPE_TO_VALUE')
        raise Exception()

    reduced_brand = reduce_brand(brand)
    value: float = 1.2 * REDUCED_BRAND_TO_VALUE[reduced_brand] * ITEM_TYPE_TO_VALUE[item_type]
    return round(value / 10) * 10