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
        todo = Todo()
        todo['uid'] = f"task-{task.id}"
        todo['summary'] = task.name
        if task.done:
            todo['status'] = 'COMPLETED'
            todo['completed'] = vDatetime(task.done)
        else:
            todo['status'] = 'NEEDS-ACTION'

        if task.deadline:
            todo['due'] = vDatetime(task.deadline)

        cal = Calendar()
        cal.add_component(todo)
        yield todo['uid'], cal


def get_shoppingitems() -> list[Calendar]:
    for item in Item.objects.all():
        todo = Todo()
        todo['uid'] = f"shoppingitem-{item.id}"
        todo['summary'] = item.name
        if item.in_cart:
            todo['status'] = 'COMPLETED'
        else:
            todo['status'] = 'NEEDS-ACTION'

        cal = Calendar()
        cal.add_component(todo)
        yield todo['uid'], cal


def get_task(id: int) -> Calendar:
    task = Task.objects.get(id=id)
    todo = Todo()
    todo['uid'] = f"task-{task.id}"
    todo['summary'] = task.name
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


def get_shoppingitem(id: int) -> Calendar:
    item = Item.objects.get(id=id)
    todo = Todo()
    todo['uid'] = f"shoppingitem-{item.id}"
    todo['summary'] = item.name
    if item.in_cart:
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    cal = Calendar()
    cal.add_component(todo)
    return cal
