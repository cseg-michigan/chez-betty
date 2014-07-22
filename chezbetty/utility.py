import datetime
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
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).date()
    elif period == 'day_each':
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).weekday()
    elif period == 'hour_each':
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).hour


    if 'each' in period:
        # If we are grouping in a very finite set of bins (like days of the
        # week), then use a hash map instead of a list as a return
        sums = {}
        for (item_period, items) in itertools.groupby(rows, group_function):
            total = 0
            for item in items:
                total += item.summable
            sums[item_period] = total

    else:
        # If we are grouping in a long list of things (days over some range)
        # then a list is better.
        sums = []
        for (item_period, items) in itertools.groupby(rows, group_function):
            total = 0
            for item in items:
                total += item.summable
            sums.append({period: item_period, 'total': total})

    return sums
