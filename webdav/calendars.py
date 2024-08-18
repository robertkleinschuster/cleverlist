from webdav.models import Resource


def ensure_root() -> Resource:
    exists = Resource.objects.filter(
        user=None,
        name='calendars',
        parent=None
    ).exists()
    if exists:
        resource = Resource.objects.get(
            user=None,
            name='calendars',
            parent=None
        )
        if resource.user_id:
            resource.user = None
            resource.save()
        return resource
    else:
        return Resource.objects.create(
            user=None,
            name='calendars',
            collection=True
        )


def ensure_calendar(root: Resource, name: str, displayname: str) -> Resource:
    exists = Resource.objects.filter(
        parent=root,
        name=name,
    ).exists()
    if exists:
        resource = Resource.objects.get(
            parent=root,
            name=name,
        )
        if resource.user_id:
            resource.user = None
            resource.save()
        return resource
    else:
        resource = Resource.objects.create(
            user=None,
            parent=root,
            name=name,
            collection=True,
        )
        resource.prop_set.create(
            name='{DAV:}displayname',
            value=displayname
        )
        resource.prop_set.create(
            name='{urn:ietf:params:xml:ns:caldav}supported-calendar-component-set',
            is_xml=True,
            value='<B:comp xmlns:B="urn:ietf:params:xml:ns:caldav" xmlns:A="DAV:" name="VTODO"/>'
        )
        resource.prop_set.create(
            name='{urn:ietf:params:xml:ns:caldav}calendar-free-busy-set',
            is_xml=True,
            value='<NO xmlns:A="DAV:" xmlns:B="urn:ietf:params:xml:ns:caldav"/>'
        )
        resource.prop_set.create(
            name='{urn:ietf:params:xml:ns:caldav}calendar-timezone',
            value='''
BEGIN:VCALENDAR
VERSION:2.0
CALSCALE:GREGORIAN
BEGIN:VTIMEZONE
TZID:Europe/Vienna
BEGIN:DAYLIGHT
TZOFFSETFROM:+0100
RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU
DTSTART:19810329T020000
TZNAME:MESZ
TZOFFSETTO:+0200
END:DAYLIGHT
BEGIN:STANDARD
TZOFFSETFROM:+0200
RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU
DTSTART:19961027T030000
TZNAME:MEZ
TZOFFSETTO:+0100
END:STANDARD
END:VTIMEZONE
END:VCALENDAR
'''
        )
        return resource
