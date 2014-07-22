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

class InvalidGroupPeriod(Exception):
    pass

def group(rows, period='day'):

    def group_month(i):
        dt = i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        return datetime.date(dt.year, dt.month, 1)
    def group_year(i):
        dt = i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None)
        return datetime.date(dt.year, 1, 1)

    if period == 'day':
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).date()
    elif period == 'month':
        group_function = group_month
    elif period == 'year':
        group_function = group_year
    elif period == 'day_each':
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).weekday()
    elif period == 'hour_each':
        group_function = lambda i: i.timestamp.replace(tzinfo=datetime.timezone.utc).astimezone(tz=None).hour
    else:
        raise(InvalidGroupPeriod(period))


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
            sums.append((item_period, total))

    return sums
