from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from lxml import etree
from caldav import helper

# Create your views here.

# Hardcoded to-do lists (events)
TODO_LISTS = {
    '1': [
        {
            'uid': 'todo-1',
            'summary': 'Buy groceries',
            'dtstart': '20230822T090000',
            'dtend': '20230822T100000',
        },
        {
            'uid': 'todo-2',
            'summary': 'Walk the dog',
            'dtstart': '20230822T110000',
            'dtend': '20230822T113000',
        },
    ],
    '2': [
        {
            'uid': 'todo-3',
            'summary': 'Finish Django project',
            'dtstart': '20230822T120000',
            'dtend': '20230822T140000',
        },
    ],
}


@csrf_exempt
def well_known_caldav_redirect(request):
    return HttpResponseRedirect('/caldav/principal/')


@csrf_exempt
def principal_handler(request):
    if request.method != 'PROPFIND':
        return HttpResponseNotAllowed(['PROPFIND'])

    # Define namespaces
    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}

    # Create the multistatus element
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    # Create a response element for the principal resource
    response = etree.SubElement(multistatus, '{DAV:}response')
    href = etree.SubElement(response, '{DAV:}href')
    href.text = '/caldav/principal/'

    # Create propstat element to hold properties
    propstat = etree.SubElement(response, '{DAV:}propstat')
    prop = etree.SubElement(propstat, '{DAV:}prop')

    # Add current-user-principal
    current_user_principal = etree.SubElement(prop, '{DAV:}current-user-principal')
    principal_href = etree.SubElement(current_user_principal, '{DAV:}href')
    principal_href.text = '/caldav/principal/'

    # Add calendar-home-set
    calendar_home_set = etree.SubElement(prop, '{urn:ietf:params:xml:ns:caldav}calendar-home-set')
    home_href = etree.SubElement(calendar_home_set, '{DAV:}href')
    home_href.text = '/caldav/home/'  # This should be the URL where calendars are located

    # Add displayname
    displayname = etree.SubElement(prop, '{DAV:}displayname')
    displayname.text = 'Cleverlist'

    # Add supported-calendar-component-set
    supported_calendar_component_set = etree.SubElement(
        prop, '{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set'
    )
    # etree.SubElement(supported_calendar_component_set, '{urn:ietf:params:xml:ns:caldav}comp', name='VEVENT')
    etree.SubElement(supported_calendar_component_set, '{urn:ietf:params:xml:ns:caldav}comp', name='VTODO')

    # Set the status for the propstat
    status = etree.SubElement(propstat, '{DAV:}status')
    status.text = 'HTTP/1.1 200 OK'

    # Convert the XML tree to a string
    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


@csrf_exempt
def home_handler(request):
    if request.method != 'PROPFIND':
        return HttpResponseNotAllowed(['PROPFIND'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    helper.add_tasklist(multistatus, 'tasks', 'Aufgaben')
    helper.add_tasklist(multistatus, 'shoppinglist', 'Einkaufsliste')

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


@csrf_exempt
def tasklist_handler(request, calendar_id):
    if request.method not in ['PROPFIND', 'REPORT']:
        return HttpResponseNotAllowed(['PROPFIND', 'REPORT'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    if calendar_id is 'tasks':
        for task_id, task in helper.get_tasks():
            helper.add_todo(multistatus, task, calendar_id, task_id)

    if calendar_id is 'shoppinglist':
        for task_id, task in helper.get_shoppingitems():
            helper.add_todo(multistatus, task, calendar_id, task_id)

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


@csrf_exempt
def task_handler(request, calendar_id, event_uid):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    calendar = None
    if calendar_id == 'tasks':
        calendar = helper.get_task(int(event_uid))

    if calendar_id == 'shoppinglist':
        calendar = helper.get_shoppingitem(int(event_uid))

    if calendar is not None:
        return HttpResponse(calendar.to_ical().decode('utf-8'), content_type='text/calendar')

    return HttpResponse(status=404)
