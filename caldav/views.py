from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from lxml import etree
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


def options_handler(request):
    if request.method == 'OPTIONS':
        response = HttpResponse()
        response['Allow'] = 'OPTIONS, PROPFIND, GET'
        response['DAV'] = '1, 2, calendar-access'
        response['Content-Length'] = '0'
        return response
    else:
        return HttpResponseNotAllowed(['OPTIONS'])


def well_known_caldav_redirect(request):
    return HttpResponseRedirect('/caldav/principal/')


def principal_handler(request):
    if request.method != 'PROPFIND':
        return HttpResponseNotAllowed(['PROPFIND'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    response = etree.SubElement(multistatus, '{DAV:}response')
    href = etree.SubElement(response, '{DAV:}href')
    href.text = '/caldav/principal/'

    propstat = etree.SubElement(response, '{DAV:}propstat')
    prop = etree.SubElement(propstat, '{DAV:}prop')

    current_user_principal = etree.SubElement(prop, '{DAV:}current-user-principal')
    principal_href = etree.SubElement(current_user_principal, '{DAV:}href')
    principal_href.text = '/caldav/principal/'

    calendar_home_set = etree.SubElement(prop, '{urn:ietf:params:xml:ns:caldav}calendar-home-set')
    home_href = etree.SubElement(calendar_home_set, '{DAV:}href')
    home_href.text = '/caldav/home/'

    status = etree.SubElement(propstat, '{DAV:}status')
    status.text = 'HTTP/1.1 200 OK'

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


def home_handler(request):
    if request.method != 'PROPFIND':
        return HttpResponseNotAllowed(['PROPFIND'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    for calendar_id in TODO_LISTS.keys():
        response = etree.SubElement(multistatus, '{DAV:}response')
        href = etree.SubElement(response, '{DAV:}href')
        href.text = f'/caldav/{calendar_id}/'

        propstat = etree.SubElement(response, '{DAV:}propstat')
        prop = etree.SubElement(propstat, '{DAV:}prop')

        displayname = etree.SubElement(prop, '{DAV:}displayname')
        displayname.text = f'To-Do List {calendar_id}'

        resourcetype = etree.SubElement(prop, '{DAV:}resourcetype')
        etree.SubElement(resourcetype, '{DAV:}collection')
        etree.SubElement(resourcetype, '{urn:ietf:params:xml:ns:caldav}calendar')

        supported_calendar_component_set = etree.SubElement(prop, '{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set')
        etree.SubElement(supported_calendar_component_set, '{urn:ietf:params:xml:ns:caldav}comp', name='VTODO')

        status = etree.SubElement(propstat, '{DAV:}status')
        status.text = 'HTTP/1.1 200 OK'

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


def propfind(request, calendar_id):
    if request.method != 'PROPFIND':
        return HttpResponseNotAllowed(['PROPFIND'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)

    todos = TODO_LISTS.get(calendar_id, [])

    for todo in todos:
        response = etree.SubElement(multistatus, '{DAV:}response')
        href = etree.SubElement(response, '{DAV:}href')
        href.text = f'/caldav/{calendar_id}/{todo["uid"]}/'

        propstat = etree.SubElement(response, '{DAV:}propstat')
        prop = etree.SubElement(propstat, '{DAV:}prop')

        etree.SubElement(prop, '{DAV:}getetag').text = f'"{todo["uid"]}"'
        calendar_data = etree.SubElement(prop, '{urn:ietf:params:xml:ns:caldav}calendar-data')

        icalendar_data = (
            f"BEGIN:VCALENDAR\r\n"
            f"VERSION:2.0\r\n"
            f"BEGIN:VTODO\r\n"
            f"UID:{todo['uid']}\r\n"
            f"SUMMARY:{todo['summary']}\r\n"
            f"DTSTART:{todo['dtstart']}\r\n"
            f"DTEND:{todo['dtend']}\r\n"
            f"END:VTODO\r\n"
            f"END:VCALENDAR\r\n"
        )
        calendar_data.text = icalendar_data

        status = etree.SubElement(propstat, '{DAV:}status')
        status.text = 'HTTP/1.1 200 OK'

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


def get_event(request, calendar_id, event_uid):
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    todos = TODO_LISTS.get(calendar_id, [])
    todo = next((t for t in todos if t['uid'] == event_uid), None)

    if todo is None:
        return HttpResponse(status=404)

    icalendar_data = (
        f"BEGIN:VCALENDAR\r\n"
        f"VERSION:2.0\r\n"
        f"BEGIN:VTODO\r\n"
        f"UID:{todo['uid']}\r\n"
        f"SUMMARY:{todo['summary']}\r\n"
        f"DTSTART:{todo['dtstart']}\r\n"
        f"DTEND:{todo['dtend']}\r\n"
        f"END:VTODO\r\n"
        f"END:VCALENDAR\r\n"
    )

    return HttpResponse(icalendar_data, content_type='text/calendar')