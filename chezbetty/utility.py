import itertools
import qrcode
import qrcode.image.svg

try:
    import lxml.etree as ET
except ImportError:
    import xml.etree.ElementTree as ET


def string_to_qrcode(s):
    factory = qrcode.image.svg.SvgPathImage
    img = qrcode.make(s, image_factory=factory, box_size=14,
        version=4,
        border=0)
    img.save('/dev/null')   # This is needed, I swear.
    return ET.tostring(img._img).decode('utf-8')

def group(rows, period='day'):
    if period == 'day':
        group_function = lambda i: i.timestamp.date()

    sums = []
    for (item_period, items) in itertools.groupby(rows, group_function):
        total = 0
        for item in items:
            total += item.summable
        sums.append({period: item_period, 'total': total})
    return sums
