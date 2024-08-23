from django.http import HttpRequest
from django.utils import timezone
from icalendar import Todo, vDatetime, Calendar
from lxml import etree

from inventory.models import ProductWithStock
from shopping.models import Item
from todo.models import Task


def add_tasklist(multistatus: etree.Element, id: str, name: str, color='#FF0000'):
    response = etree.SubElement(multistatus, '{DAV:}response')
    href = etree.SubElement(response, '{DAV:}href')
    href.text = f'/caldav/{id}/'

    propstat = etree.SubElement(response, '{DAV:}propstat')
    prop = etree.SubElement(propstat, '{DAV:}prop')

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
    for task in Task.objects.prefetch_related('tags').all():
        cal = get_task(task)
        yield cal.subcomponents[0]['uid'], cal


def get_shoppingitems() -> list[Calendar]:
    for item in Item.objects.prefetch_related('tags').all():
        cal = get_shoppingitem(item)
        yield cal.subcomponents[0]['uid'], cal


def get_shoppingcart() -> list[Calendar]:
    for item in Item.objects.prefetch_related('tags').filter(in_cart=True).all():
        cal = get_shoppingitem(item)
        yield cal.subcomponents[0]['uid'], cal


def get_inventory() -> list[Calendar]:
    for item in ProductWithStock.default_manager.all():
        cal = get_inventory_item(item)
        yield cal.subcomponents[0]['uid'], cal


def get_task(uuid_or_task: str | Task) -> Calendar:
    if isinstance(uuid_or_task, Task):
        task = uuid_or_task
    else:
        task = Task.objects.get(uuid=uuid_or_task)
    todo = Todo()
    todo['uid'] = task.uuid
    todo['summary'] = str(task)
    if task.done:
        todo['status'] = 'COMPLETED'
        todo['completed'] = vDatetime(task.done)
    else:
        todo['status'] = 'NEEDS-ACTION'

    if task.deadline:
        todo['due'] = vDatetime(task.deadline)

    todo['description'] = ", ".join([str(tag) for tag in task.tags.all()])

    cal = Calendar()
    cal.add_component(todo)
    return cal


def get_shoppingitem(uuid_or_item: str | Item) -> Calendar:
    if isinstance(uuid_or_item, Item):
        item = uuid_or_item
    else:
        item = Item.objects.get(uuid=uuid_or_item)
    todo = Todo()
    todo['uid'] = item.uuid
    todo['summary'] = str(item)
    if item.in_cart:
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    todo['description'] = ", ".join([str(tag) for tag in item.tags.all()])

    cal = Calendar()
    cal.add_component(todo)
    return cal


def get_inventory_item(uuid_or_item: str | ProductWithStock) -> Calendar:
    if isinstance(uuid_or_item, ProductWithStock):
        item = uuid_or_item
    else:
        item = ProductWithStock.default_manager.get(uuid=uuid_or_item)
    todo = Todo()
    todo['uid'] = item.uuid
    todo['summary'] = f'{item.stock} x {item.name} (Mind. {item.minimum_stock})'
    if item.stock == 0:
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    cal = Calendar()
    cal.add_component(todo)
    return cal


def calendar_from_request(request: HttpRequest) -> Calendar:
    return Calendar.from_ical(request.body)


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

    todo = cal.subcomponents[0]
    if todo['status'] == 'NEEDS-ACTION' and task.done:
        task.done = None
        changed = True

    if todo['status'] == 'COMPLETED' and task.done is None:
        task.done = timezone.now()
        changed = True

    summary = str(todo['summary'])
    if summary and summary != task.name:
        task.name = summary
        changed = True

    if todo.get('due') and task.deadline is None:
        task.deadline = todo['due'].dt
        changed = True

    if todo.get('due') is None and task.deadline:
        task.deadline = None
        changed = True

    if changed:
        task.save()


def change_shoppingitem(uuid: str, cal: Calendar):
    item = Item.objects.get(uuid=uuid)
    todo = cal.subcomponents[0]
    if todo['status'] == 'NEEDS-ACTION' and item.in_cart is True:
        item.in_cart = False
        item.save()

    if todo['status'] == 'COMPLETED' and item.in_cart is False:
        item.in_cart = True
        item.save()


def change_inventory(uuid: str, cal: Calendar):
    item = ProductWithStock.default_manager.get(uuid=uuid)
    todo = cal.subcomponents[0]

    if todo['status'] == 'COMPLETED' and item.stock > 0:
        productstock = item.productstock_set.filter(stock__gt=0).first()
        productstock.stock -= 1
        productstock.save()


def delete_task(uuid: str):
    Task.objects.get(uuid=uuid).delete()


def delete_shoppingitem(uuid: str):
    Item.objects.get(uuid=uuid).delete()
