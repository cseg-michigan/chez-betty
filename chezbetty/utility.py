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

