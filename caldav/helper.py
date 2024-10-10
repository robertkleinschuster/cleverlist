import hashlib

from django.http import HttpRequest
from django.utils import timezone
from icalendar import Todo, vDatetime, Calendar, Alarm
from lxml import etree

from caldav.models import CalDAVTasklist
from inventory.admin import add_shopping_item
from inventory.models import ProductWithStock
from master.models import Product
from shopping.admin import move_to_inventory
from shopping.models import Item
from todo.models import Task


def add_tasklist(multistatus: etree.Element, id: str, name: str, color='#FF0000', etag: str = None):
    response = etree.SubElement(multistatus, '{DAV:}response')
    href = etree.SubElement(response, '{DAV:}href')
    href.text = f'/caldav/{id}/'

    propstat = etree.SubElement(response, '{DAV:}propstat')
    prop = etree.SubElement(propstat, '{DAV:}prop')

    if etag is not None:
        etagElem = etree.SubElement(prop, "{DAV:}getetag")
        etagElem.text = etag

    displayname = etree.SubElement(prop, '{DAV:}displayname')
    displayname.text = name

    resourcetype = etree.SubElement(prop, '{DAV:}resourcetype')
    etree.SubElement(resourcetype, '{DAV:}collection')
    etree.SubElement(resourcetype, '{urn:ietf:params:xml:ns:caldav}calendar')

    supported_calendar_component_set = etree.SubElement(
        prop, '{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set'
    )
    etree.SubElement(supported_calendar_component_set, '{urn:ietf:params:xml:ns:caldav}comp', name='VTODO')

    calendar_color = etree.SubElement(prop, '{http://apple.com/ns/ical/}calendar-color')
    calendar_color.text = color  # The color should be a hex value like "#FF0000" for red

    status = etree.SubElement(propstat, '{DAV:}status')
    status.text = 'HTTP/1.1 200 OK'


def add_todo(multistatus: etree.Element, calendar_id: str, event_id: str, icalendar_data: Calendar):
    response = etree.SubElement(multistatus, '{DAV:}response')
    href = etree.SubElement(response, '{DAV:}href')
    href.text = f'/caldav/{calendar_id}/{event_id}/'  # Make sure this is correct

    propstat = etree.SubElement(response, '{DAV:}propstat')
    prop = etree.SubElement(propstat, '{DAV:}prop')

    # Ensure getetag is correct
    etree.SubElement(prop, '{DAV:}getetag').text = f'"{event_id}"'

    # Add calendar-data element
    calendar_data = etree.SubElement(prop, '{urn:ietf:params:xml:ns:caldav}calendar-data')

    # Generate iCalendar data for the VTODO component

    calendar_data.text = icalendar_data.to_ical().decode('utf-8')  # Ensure this is correct

    status = etree.SubElement(propstat, '{DAV:}status')
    status.text = 'HTTP/1.1 200 OK'


def get_tasks() -> list[Calendar]:
    for task in Task.objects.order_by('name').prefetch_related('tags').all():
        cal = get_task(task)
        yield cal.subcomponents[0]['uid'], cal


def get_shoppingitems() -> list[Calendar]:
    for item in Item.objects.order_by('name').prefetch_related('tags').filter(in_cart=False).all():
        cal = get_shoppingitem(item, False)
        yield cal.subcomponents[0]['uid'], cal


def get_shoppingcart() -> list[Calendar]:
    for item in Item.objects.order_by('name').prefetch_related('tags').filter(in_cart=True).all():
        cal = get_shoppingitem(item, True)
        yield cal.subcomponents[0]['uid'], cal


def get_inventory() -> list[Calendar]:
    for item in ProductWithStock.default_manager.order_by('name').all():
        cal = get_inventory_item(item)
        yield cal.subcomponents[0]['uid'], cal


def get_task(uuid_or_task: str | Task) -> Calendar:
    if isinstance(uuid_or_task, Task):
        task = uuid_or_task
    else:
        task = Task.objects.get(uuid=uuid_or_task)
    todo = Todo()
    todo['dtstamp'] = vDatetime(task.updated_at)
    todo['uid'] = task.uuid
    todo['summary'] = str(task)
    if task.done:
        todo['status'] = 'COMPLETED'
        todo['completed'] = vDatetime(task.done)
    else:
        todo['status'] = 'NEEDS-ACTION'

    if task.deadline:
        todo['due'] = vDatetime(task.deadline)
        alarm = Alarm()
        alarm['action'] = 'DISPLAY'
        alarm['trigger'] = vDatetime(task.deadline)
        todo.add_component(alarm)

    todo['description'] = ", ".join([str(tag) for tag in task.tags.all()])

    cal = Calendar()
    cal['version'] = '2.0'
    cal['prodid'] = '-//CleverList//1.0//DE'
    cal.add_component(todo)
    return cal


def get_shoppingitem(uuid_or_item: str | Item, is_cart: bool) -> Calendar:
    if isinstance(uuid_or_item, Item):
        item = uuid_or_item
    else:
        item = Item.objects.get(uuid=uuid_or_item)
    todo = Todo()
    todo['dtstamp'] = vDatetime(item.updated_at)
    todo['uid'] = item.uuid
    todo['summary'] = str(item)
    if is_cart:
        if item.in_cart:
            todo['status'] = 'NEEDS-ACTION'
        else:
            todo['status'] = 'COMPLETED'
    else:
        if item.in_cart:
            todo['status'] = 'COMPLETED'
        else:
            todo['status'] = 'NEEDS-ACTION'

    todo['description'] = ", ".join([str(tag) for tag in item.tags.all()])

    cal = Calendar()
    cal['version'] = '2.0'
    cal['prodid'] = '-//CleverList//1.0//DE'
    cal.add_component(todo)
    return cal


def get_inventory_item(uuid_or_item: str | ProductWithStock) -> Calendar:
    if isinstance(uuid_or_item, ProductWithStock):
        item = uuid_or_item
    else:
        item = ProductWithStock.default_manager.get(uuid=uuid_or_item)
    todo = Todo()
    todo['dtstamp'] = vDatetime(timezone.now())
    todo['uid'] = item.uuid
    if item.minimum_stock > 0:
        todo['summary'] = f'{item.stock} / {item.minimum_stock} x {item.name}'
    else:
        todo['summary'] = f'{item.stock} x {item.name}'

    if item.stock == 0:
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    cal = Calendar()
    cal['version'] = '2.0'
    cal['prodid'] = '-//CleverList//1.0//DE'
    cal.add_component(todo)
    return cal


def calendar_from_request(request: HttpRequest) -> Calendar:
    return Calendar.from_ical(request.body.decode('utf-8'))


def change_task(uuid: str, cal: Calendar):
    if not Task.objects.filter(uuid=uuid).exists():
        task = Task.objects.create(
            name='',
            uuid=uuid,
        )
        changed = True
    else:
        task = Task.objects.get(uuid=uuid)
        changed = False

    todo = cal.walk('VTODO')[0]
    if todo.get('status') == 'NEEDS-ACTION' and task.done:
        task.done = None
        changed = True

    if todo.get('status') == 'COMPLETED' and task.done is None:
        task.done = timezone.now()
        changed = True

    summary = todo.get('summary')
    if summary and summary != task.name:
        task.name = str(summary)
        changed = True

    due = None
    if todo.get('due') is not None:
        due = todo.get('due').dt

    if task.deadline != due:
        task.deadline = due
        changed = True

    if changed:
        task.save()


def change_shoppingitem_base(uuid: str, cal: Calendar, in_cart_default: bool):
    todo = cal.walk('VTODO')[0]
    summary = str(todo.get('summary'))
    if ' x ' in summary:
        quantity, name = summary.split(' x ', 2)
    else:
        quantity = 1
        name = summary

    name = str(name)

    if int(quantity) > 0:
        quantity = int(quantity)
    else:
        quantity = 1

    if not Item.objects.filter(uuid=uuid).exists():
        product = Product.objects.filter(name__iexact=name.strip()).first()
        if product is None:
            product = Product.objects.create(
                name=name,
            )

        item = Item.objects.create(
            product=product,
            quantity=int(quantity),
            in_cart=in_cart_default,
            uuid=uuid,
        )

        name = item.name
    else:
        item = Item.objects.get(uuid=uuid)

    if item.product is None and len(name) and name != item.name:
        item.name = name
        item.save()

    if 0 < quantity != item.quantity:
        item.quantity = quantity
        item.save()

    return item, todo


def on_change_tasklist(code: str):
    CalDAVTasklist.objects.update_or_create(
        code=code,
        defaults={
            'etag': hashlib.md5(str(timezone.now()).encode('utf-8')).hexdigest(),
        }
    )


def change_shoppingitem(uuid: str, cal: Calendar):
    item, todo = change_shoppingitem_base(uuid, cal, False)
    if todo.get('status') == 'NEEDS-ACTION' and item.in_cart is True:
        item.in_cart = False
        item.save()
        on_change_tasklist('shoppingcart')

    if todo.get('status') == 'COMPLETED' and item.in_cart is False:
        item.in_cart = True
        item.save()
        on_change_tasklist('shoppingcart')


def change_shoppingcart(uuid: str, cal: Calendar):
    item, todo = change_shoppingitem_base(uuid, cal, True)
    if todo.get('status') == 'COMPLETED' and item.in_cart is True:
        move_to_inventory(None, None, Item.objects.filter(uuid=uuid))
        on_change_tasklist('inventory')


def change_inventory(uuid: str, cal: Calendar):
    item = ProductWithStock.default_manager.filter(uuid=uuid).first()
    if item is None:
        return
    todo = cal.walk('VTODO')[0]

    if todo.get('status') == 'COMPLETED' and item.stock > 0:
        productstock = item.productstock_set.filter(stock__gt=0).first()
        productstock.stock -= 1
        productstock.save()
        add_shopping_item(None, None, ProductWithStock.default_manager.filter(uuid=uuid))
        on_change_tasklist('shoppinglist')


def delete_task(uuid: str):
    Task.objects.get(uuid=uuid).delete()


def delete_shoppingitem(uuid: str):
    Item.objects.get(uuid=uuid).delete()
