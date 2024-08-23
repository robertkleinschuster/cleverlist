from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotAllowed
from django.views.decorators.csrf import csrf_exempt
from lxml import etree
from caldav import helper


# Create your views here.

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

    helper.add_tasklist(multistatus, 'tasks', 'Aufgaben', '#EE81EE')
    helper.add_tasklist(multistatus, 'shoppinglist', 'Einkaufsliste', '#FFA600')
    helper.add_tasklist(multistatus, 'shoppingcart', 'Einkaufswagen', '#FFA600')
    helper.add_tasklist(multistatus, 'inventory', 'Bestand', '#FFA600')

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


@csrf_exempt
def tasklist_handler(request, calendar_id):
    if request.method not in ['PROPFIND', 'REPORT']:
        return HttpResponseNotAllowed(['PROPFIND', 'REPORT'])

    nsmap = {'D': 'DAV:', 'C': 'urn:ietf:params:xml:ns:caldav'}
    multistatus = etree.Element('{DAV:}multistatus', nsmap=nsmap)
    if calendar_id == 'tasks':
        for task_id, task in helper.get_tasks():
            helper.add_todo(multistatus, calendar_id, task_id, task)

    if calendar_id == 'shoppinglist':
        for task_id, task in helper.get_shoppingitems():
            helper.add_todo(multistatus, calendar_id, task_id, task)

    if calendar_id == 'shoppingcart':
        for task_id, task in helper.get_shoppingcart():
            helper.add_todo(multistatus, calendar_id, task_id, task)

    if calendar_id == 'inventory':
        for task_id, task in helper.get_inventory():
            helper.add_todo(multistatus, calendar_id, task_id, task)

    xml_str = etree.tostring(multistatus, pretty_print=True).decode()
    return HttpResponse(xml_str, content_type='application/xml')


@csrf_exempt
def task_handler(request, calendar_id: str, event_uid: str):
    if event_uid.endswith('.ics'):
        event_uid = event_uid[:-4]

    if request.method == 'DELETE':
        if calendar_id == 'tasks':
            helper.delete_task(event_uid)
        if calendar_id == 'shoppinglist':
            helper.delete_shoppingitem(event_uid)
        if calendar_id == 'shoppingcart':
            helper.delete_shoppingitem(event_uid)
        return HttpResponse(status=204)

    if request.method == 'PUT':
        if calendar_id == 'tasks':
            helper.change_task(event_uid, helper.calendar_from_request(request))
        if calendar_id == 'shoppinglist':
            helper.change_shoppingitem(event_uid, helper.calendar_from_request(request))
        if calendar_id == 'shoppingcart':
            helper.change_shoppingcart(event_uid, helper.calendar_from_request(request))
        if calendar_id == 'inventory':
            helper.change_inventory(event_uid, helper.calendar_from_request(request))

        return HttpResponse(status=204)
    if request.method != 'GET':
        return HttpResponseNotAllowed(['GET'])

    calendar = None
    if calendar_id == 'tasks':
        calendar = helper.get_task(event_uid)

    if calendar_id == 'shoppinglist':
        calendar = helper.get_shoppingitem(event_uid)

    if calendar_id == 'shoppingcart':
        calendar = helper.get_shoppingitem(event_uid)

    if calendar_id == 'inventory':
        calendar = helper.get_inventory_item(event_uid)

    if calendar is not None:
        return HttpResponse(calendar.to_ical().decode('utf-8'), content_type='text/calendar')

    return HttpResponse(status=404)
