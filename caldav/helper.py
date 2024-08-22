from django.http import HttpRequest
from django.utils import timezone
from icalendar import Todo, vDatetime, Calendar
from lxml import etree

from shopping.models import Item
from todo.models import Task


def add_tasklist(multistatus: etree.Element, id: str, name: str):
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
    for task in Task.objects.all():
        cal = get_task(task)
        yield cal.subcomponents[0]['uid'], cal


def get_shoppingitems() -> list[Calendar]:
    for item in Item.objects.all():
        cal = get_shoppingitem(item)
        yield cal.subcomponents[0]['uid'], cal


def get_task(id: int | Task) -> Calendar:
    if isinstance(id, Task):
        task = id
    else:
        task = Task.objects.get(id=id)
    todo = Todo()
    todo['uid'] = f"task-{task.id}"
    todo['summary'] = str(task)
    if task.done:
        todo['status'] = 'COMPLETED'
        todo['completed'] = vDatetime(task.done)
    else:
        todo['status'] = 'NEEDS-ACTION'

    if task.deadline:
        todo['due'] = vDatetime(task.deadline)

    cal = Calendar()
    cal.add_component(todo)
    return cal


def get_shoppingitem(id: int | Item) -> Calendar:
    if isinstance(id, Item):
        item = id
    else:
        item = Item.objects.get(id=id)
    todo = Todo()
    todo['uid'] = f"shoppingitem-{item.id}"
    todo['summary'] = str(item)
    if item.in_cart:
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    cal = Calendar()
    cal.add_component(todo)
    return cal


def calendar_from_request(request: HttpRequest) -> Calendar:
    return Calendar.from_ical(request.body)


def change_task(id: int, cal: Calendar):
    if not Task.objects.filter(id=id).exists():
        task = Task.objects.create(
            name=str(id),
        )
        changed = True
    else:
        task = Task.objects.get(id=id)
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


def change_shoppingitem(id: int, cal: Calendar):
    item = Item.objects.get(id=id)
    todo = cal.subcomponents[0]
    if todo['status'] == 'NEEDS-ACTION' and item.in_cart is True:
        item.in_cart = False
        item.save()

    if todo['status'] == 'COMPLETED' and item.in_cart is False:
        item.in_cart = True
        item.save()


def delete_task(id: int):
    Task.objects.get(id=id).delete()


def delete_shoppingitem(id: int):
    Item.objects.get(id=id).delete()
