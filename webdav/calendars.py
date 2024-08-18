from django.contrib.auth.models import User

from webdav.models import Resource


def ensure_root(user: User) -> Resource:
    exists = Resource.objects.filter(
        user=user,
        name='calendars',
        parent=None
    ).exists()
    if exists:
        return Resource.objects.get(
            user=user,
            name='calendars',
            parent=None
        )
    else:
        return Resource.objects.create(
            user=user,
            name='calendars',
            collection=True
        )


def ensure_calendar(root: Resource, name: str, displayname: str) -> Resource:
    exists = Resource.objects.filter(
        parent=root,
        name=name,
    ).exists()
    if exists:
        return Resource.objects.get(
            parent=root,
            name=name,
        )
    else:
        resource = Resource.objects.create(
            user=root.user,
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
            is_xml=True,
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
