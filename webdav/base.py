from django.db.models import Q
from django.http import StreamingHttpResponse, HttpResponse, HttpResponseForbidden
from django.views.generic.base import View
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login

import webdav
from lxml import etree
from django.utils.http import http_date
from webdav.models import Resource
import base64
import types
from django.conf import settings

from .storage import FSStorage
from re import sub, compile
from django.core.exceptions import ObjectDoesNotExist
import logging

from .todo import parse_todo

user_regexp = compile(r"/(?P<user>\w+)/$")

logger = logging.getLogger(__name__)


def _check_group_sharing(user, username):
    try:
        sharing_user = User.objects.get(username=username)
        return sharing_user.groups.all() & user.groups.all()
    except ObjectDoesNotExist:
        return None


class WebDAV(View):
    http_method_names = ['get', 'put', 'propfind', 'delete',
                         'head', 'options', 'mkcol', 'proppatch', 'copy', 'move']

    collection_type = '{DAV:}collection'
    subcollection_type = None

    # add your OPTIONS Dav header extensions here
    dav_extensions = []

    root = None
    storage = None

    def __init__(self, **kwargs):
        super(WebDAV, self).__init__(**kwargs)
        if self.storage is None:
            self.storage = FSStorage()

    @csrf_exempt
    def dispatch(self, request, username, *args, **kwargs):
        if username == 'shared':
            username = None
        user = None
        # REMOTE_USER should be always honored
        if 'REMOTE_USER' in request.META:
            user = User.objects.get(username=request.META['REMOTE_USER'])
        elif 'HTTP_AUTHORIZATION' in request.META:
            auth = request.META['HTTP_AUTHORIZATION'].split()
            if len(auth) == 2:
                if auth[0].lower() == "basic":
                    uname, passwd = base64.b64decode(auth[1]).decode('utf-8').split(':')
                    user = authenticate(username=uname, password=passwd)

        if (user and user.is_active) and (
                user.username == username or username is None or _check_group_sharing(user, username)):
            login(request, user)
            request.user = user
            try:
                print('user', user)

                response = super(WebDAV, self).dispatch(
                    request, username, *args, **kwargs
                )
                dav_base = ['1']
                dav_base += getattr(settings, 'DAVVY_EXTENSIONS', [])
                response['Dav'] = ','.join(dav_base + self.dav_extensions)
            except webdav.exceptions.DavException as e:
                print('error', e.status)
                code, phrase = e.status.split(' ', 1)
                response = HttpResponse(phrase, content_type='text/plain')
                response.status_code = int(code)
                response.reason_phrase = phrase
        else:
            response = HttpResponse('Unathorized', content_type='text/plain')
            response.status_code = 401
            response['WWW-Authenticate'] = 'Basic realm="cleverlist"'

        print('response', response)
        return response

    def options(self, request, username, resource_name):
        response = HttpResponse()
        response['Allow'] = ','.join(
            [method.upper() for method in self.http_method_names]
        )
        return response

    def head(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name)
        if resource.collection:
            return HttpResponseForbidden()
        response = HttpResponse(content_type=resource.content_type)
        response['Content-Length'] = resource.size
        response[
            'Content-Disposition'] = "attachment; filename=%s" % resource.name
        return response

    def get(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name)

        if resource.collection:
            return HttpResponseForbidden()

        response = StreamingHttpResponse(
            self.storage.retrieve(resource),
            content_type=resource.content_type
        )

        response['Content-Length'] = resource.size
        response[
            'Content-Disposition'] = "attachment; filename=%s" % resource.name
        return response

    def delete(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name)

        # you can't delete protected resources
        if resource.protected:
            return HttpResponseForbidden()

        depth = request.META.get('HTTP_DEPTH', 'infinity')
        # return forbidden if there are still items in the collection and
        # Depth is not 'infinity'
        # this is not standard-compliant, but should increase security
        if resource.collection and depth != 'infinity':
            if resource.resource_set.count() > 0:
                return HttpResponseForbidden()

        self.storage.delete(resource)
        resource.delete()
        return HttpResponse(status=204)

    def _get_destination(self, request, username, resource_name):
        destination = request.META['HTTP_DESTINATION']
        # ignore http(s) schema
        destination = sub(r"^http[s]*://", "", destination)

        base = request.META['HTTP_HOST'] + request.path[:-len(resource_name)]

        try:
            # destination user could be different
            destination_user = user_regexp.search(
                destination[:-len(resource_name)]
            ).group('user')

            # remove source user from base
            base = user_regexp.sub("/", base)
            if not destination.startswith(base):
                raise webdav.exceptions.BadGateway()
        except AttributeError:  # if something goes wrong while catching the user
            destination_user = username
        finally:
            # return destination resource and related user
            return destination[len(base) + len(destination_user) + 1:].rstrip('/'), destination_user

    def move(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name)
        # depth = request.META.get('HTTP_DEPTH', 'infinity')
        overwrite = request.META.get('HTTP_OVERWRITE', 'T')

        destination, destination_user = self._get_destination(
            request, username, resource_name)

        result = webdav.created

        try:
            resource2 = self.get_resource(
                request, destination_user, destination)
            if overwrite == 'F':
                raise webdav.exceptions.PreconditionFailed()
            elif overwrite == 'T':
                result = webdav.nocontent
        except webdav.exceptions.NotFound:
            resource2 = self.get_resource(
                request, destination_user, destination, create=True)

        # copy the resource
        resource2.collection = resource.collection
        resource2.uuid = resource.uuid
        resource2.size = resource.size
        resource2.content_type = resource.content_type
        resource2.created_at = resource.created_at
        resource2.save()

        # move properties
        for prop in resource.prop_set.all():
            prop.resource = resource2
            prop.save()

        # move children
        if resource.collection:
            for child in resource.resource_set.all():
                # first check for another child with the same attributes
                try:
                    twin = Resource.objects.get(
                        parent=resource2, name=child.name)
                    if overwrite == 'T':
                        twin.delete()
                        raise Resource.DoesNotExist()
                    else:
                        raise webdav.exceptions.PreconditionFailed()
                except Resource.DoesNotExist:
                    child.parent = resource2
                    child.save()

        # destroy the old resource
        resource.delete()

        return result(request)

    def _copy_resource(self, request, resource: Resource, destination, overwrite):
        result = webdav.created

        try:
            resource2 = self.get_resource(request, resource.username, destination)
            if overwrite == 'F':
                raise webdav.exceptions.PreconditionFailed()
            elif overwrite == 'T':
                result = webdav.nocontent
        except webdav.exceptions.NotFound:
            resource2 = self.get_resource(
                request, resource.username, destination, create=True)

        # copy the resource
        resource2.collection = resource.collection
        resource2.uuid = resource.uuid
        resource2.size = resource.size
        resource2.content_type = resource.content_type
        resource2.created_at = resource.created_at
        resource2.save()

        # copy properties
        for prop in resource.prop_set.all():
            prop.pk = None
            prop.resource = resource2
            prop.save()

        return result

    def _copy_coll(self, request, resource, destination, overwrite):
        result = self._copy_resource(request, resource, destination, overwrite)
        if resource.collection:
            for child in resource.resource_set.all():
                self._copy_coll(
                    request, child, destination + '/' + child.name, overwrite)
        return result

    def copy(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name)
        overwrite = request.META.get('HTTP_OVERWRITE', 'T')
        depth = request.META.get('HTTP_DEPTH', 'infinity')

        destination = self._get_destination(request, resource_name)

        if resource.collection and depth == 'infinity':
            result = self._copy_coll(request, resource, destination, overwrite)
        else:
            result = self._copy_resource(
                request, resource, destination, overwrite)

        return result(request)

    def put(self, request, username, resource_name):
        resource = self.get_resource(request, username, resource_name, create=True)
        resource.content_type = request.META.get(
            'CONTENT_TYPE', 'application/octet-stream'
        )
        resource.size = int(request.META['CONTENT_LENGTH'])
        resource.save()
        self.storage.store(request, resource)
        if resource.task_id:
            task = resource.task
            todo = parse_todo(self.storage.retrieve_string(resource))
            task.name = todo.summary
            task.deadline = todo.due
            task.done = todo.completed
            task.save()

        if resource.shoppingitem_id:
            shoppingitem = resource.shoppingitem
            todo = parse_todo(self.storage.retrieve_string(resource))
            shoppingitem.in_cart = todo.completed is not None
            shoppingitem.save()

        return webdav.created(request)

    def mkcol(self, request, username, resource_name):
        cl = 0
        if 'CONTENT_LENGTH' in request.META and len(request.META['CONTENT_LENGTH']) > 0:
            cl = int(request.META['CONTENT_LENGTH'])
        if cl > 0:
            raise webdav.exceptions.UnsupportedMediaType()
        self.get_resource(
            request, username, resource_name, create=True, collection=True, strict=True
        )
        return webdav.created(request)

    def _propfind_response(self, request, href, resource, requested_props):
        response_props = resource.properties(self, request, requested_props)
        multistatus_response = etree.Element('{DAV:}response')
        multistatus_response_href = etree.Element('{DAV:}href')

        if resource.collection:
            href = href.rstrip('/') + '/'
        try:
            scheme = request.scheme
        except:
            scheme = request.META['wsgi.url_scheme']

        multistatus_response_href.text = scheme + \
                                         '://' + request.META['HTTP_HOST'] + href
        multistatus_response.append(multistatus_response_href)

        for prop in response_props:
            propstat = etree.Element('{DAV:}propstat')
            multistatus_response.append(propstat)
            tag, value, status = prop
            prop_element = etree.Element('{DAV:}prop')
            prop_element_item = etree.Element(tag)
            if isinstance(value, etree._Element):
                prop_element_item.append(value)
            elif isinstance(value, list) or isinstance(value, types.GeneratorType):
                for item in value:
                    prop_element_item.append(item)
            else:
                if value != '':
                    prop_element_item.text = value
            prop_element.append(prop_element_item)
            propstat.append(prop_element)
            propstat_status = etree.Element('{DAV:}status')
            propstat_status.text = request.META[
                                       'SERVER_PROTOCOL'] + ' ' + status
            propstat.append(propstat_status)

        return multistatus_response

    def _proppatch_response(self, request, href, resource, requested_props):
        multistatus_response = etree.Element('{DAV:}response')
        multistatus_response_href = etree.Element('{DAV:}href')
        if resource.collection:
            href = href.rstrip('/') + '/'
        multistatus_response_href.text = href
        multistatus_response.append(multistatus_response_href)
        for prop in requested_props:
            propstat = etree.Element('{DAV:}propstat')
            multistatus_response.append(propstat)
            tag, status = prop
            prop_element = etree.Element('{DAV:}prop')
            prop_element.append(etree.Element(tag))
            propstat.append(prop_element)
            propstat_status = etree.Element('{DAV:}status')
            propstat_status.text = request.META[
                                       'SERVER_PROTOCOL'] + ' ' + status
            propstat.append(propstat_status)

        return multistatus_response

    def propfind(self, request, username, resource_name):
        return self._propfinder(request, username, resource_name)

    def _propfinder(self, request, username, resource_name, shared=False):
        resource = self.get_resource(request, username, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise webdav.exceptions.BadRequest()

        logger.debug(etree.tostring(dom, pretty_print=True))

        props = dom.find('{DAV:}prop')
        requested_props = [prop.tag for prop in props]
        depth = request.META.get('HTTP_DEPTH', 'infinity')

        doc = etree.Element('{DAV:}multistatus')

        multistatus_response = self._propfind_response(
            request,
            request.path,
            resource,
            requested_props
        )
        doc.append(multistatus_response)

        if depth == '1':
            resources = Resource.objects.prefetch_related('prop_set').filter(parent=resource)

            if shared:  # we skip it if unnecessary
                # add shared resources from groups
                shared_resources = Resource.objects.prefetch_related('prop_set').filter(
                    Q(user=None) & Q(parent__isnull=False) | Q(groups__in=request.user.groups.all())
                )

                # consider only shared resources having the same progenitor
                # so, if resource is a calendar, only calendars, and so on...
                resource_progenitor = resource.progenitor.name if resource.progenitor else self.root
                shared_resources_id = [r.id
                                       for r in shared_resources
                                       if r.progenitor.name == resource_progenitor
                                       ]

                resources |= shared_resources.filter(
                    id__in=shared_resources_id)

            for resource in resources:
                resource_username = resource.username
                if resource_username is None:
                    resource_username = 'shared'

                multistatus_response = self._propfind_response(
                    request,
                    sub(
                        r"%s$" % (username),
                        "%s" % (resource_username),
                        request.path.rstrip("/")
                    ) + "/" + resource.name,
                    resource,
                    requested_props
                )
                doc.append(multistatus_response)

        logger.debug("%s", etree.tostring(doc, pretty_print=True))

        response = HttpResponse(
            etree.tostring(doc, pretty_print=True),
            content_type='text/xml; charset=utf-8'
        )

        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response

    def proppatch(self, request, user, resource_name):
        resource = self.get_resource(request, user, resource_name)

        try:
            dom = etree.fromstring(request.read())
        except:
            raise webdav.exceptions.BadRequest()

        # print etree.tostring(dom, pretty_print=True)

        requested_props = []

        for setremove_item in dom:
            props = setremove_item.find('{DAV:}prop')
            if props is None:
                props = []
            # top-down must be respected
            for prop in props:
                if setremove_item.tag == '{DAV:}set':
                    try:
                        resource.set_prop(self, request, prop.tag, prop)
                        requested_props.append((prop.tag, '200 OK'))
                    except webdav.exceptions.DavException as e:
                        requested_props.append((prop.tag, e.status))
                elif setremove_item.tag == '{DAV:}remove':
                    try:
                        resource.del_prop(self, request, prop.tag)
                        requested_props.append((prop.tag, '200 OK'))
                    except webdav.exceptions.DavException as e:
                        requested_props.append((prop.tag, e.status))

        doc = etree.Element('{DAV:}multistatus')

        multistatus_response = self._proppatch_response(
            request, request.path, resource, requested_props)
        doc.append(multistatus_response)

        # print etree.tostring(doc, pretty_print=True)

        response = HttpResponse(
            etree.tostring(doc, pretty_print=True), content_type='text/xml; charset=utf-8')
        response.status_code = 207
        response.reason_phrase = 'Multi-Status'
        return response

    def _get_root(self, user: User):
        try:
            resource = Resource.objects.get(
                name=self.root, user=user, parent=None, collection=True)
        except Resource.DoesNotExist:
            resource = Resource.objects.create(
                name=self.root, user=user, parent=None, collection=True)
        return resource

    def get_resource(self, request, username: str | None, resource_name: str, create=False, collection=False,
                     strict=False):
        resource_user = None
        if username is not None:
            resource_user = User.objects.get(username=username)

        # remove final slashes
        resource_name = resource_name.rstrip('/')
        parent = self._get_root(resource_user)

        if not resource_name:
            return parent
        # split the name
        parts = resource_name.split('/')

        # skip the last item
        # on error, returns conflict
        # returns root in case of '/'
        for part in parts[:-1]:
            try:
                resource_part = Resource.objects.get(
                    user=resource_user, parent=parent, name=part
                )
                if not resource_part.collection:
                    raise Resource.DoesNotExist()
            except Resource.DoesNotExist:
                raise webdav.exceptions.Conflict()
            parent = resource_part

        # now check for the requested item
        try:
            resource = Resource.objects.prefetch_related('prop_set').get(
                user=resource_user, parent=parent, name=parts[-1]
            )
            if strict and create:
                raise webdav.exceptions.AlreadyExists()
        except Resource.DoesNotExist:
            if create:
                resource = Resource.objects.create(
                    user=resource_user,
                    parent=parent,
                    name=parts[-1],
                    collection=collection
                )
            else:
                print('not found in get_resource resource_user: ', resource_user, ' resource_name: ', parts[-1])
                raise webdav.exceptions.NotFound()
        return resource


def prop_dav_resourcetype(dav, request, resource):
    if resource.collection:
        # is it a subcollection ?
        if resource.parent and dav.subcollection_type is not None:
            if isinstance(dav.subcollection_type, list):
                rtypes = []
                for rtype in dav.subcollection_type:
                    rtypes.append(webdav.xml_node(rtype))
                return rtypes
            return webdav.xml_node(dav.subcollection_type)
        if isinstance(dav.collection_type, list):
            rtypes = []
            for rtype in dav.collection_type:
                rtypes.append(webdav.xml_node(rtype))
            return rtypes
        return webdav.xml_node(dav.collection_type)
    return ''


def prop_dav_getcontentlength(dav, request, resource):
    if not resource.collection:
        try:
            return str(resource.size)
        except:
            return '0'


def prop_dav_getetag(dav, request, resource):
    return str(resource.updated_at.strftime('%s'))


def prop_dav_getcontenttype(dav, request, resource):
    if not resource.collection:
        return resource.content_type
    return 'httpd/unix-directory'


def prop_dav_getlastmodified(dav, request, resource):
    return http_date(int(resource.updated_at.strftime('%s')))


def prop_dav_creationdate(dav, request, resource):
    return http_date(int(resource.created_at.strftime('%s')))


def prop_dav_current_user_principal(dav, request, resource):
    current_user_principal = getattr(
        settings, 'WEBDAV_CURRENT_USER_PRINCIPAL_BASE', None
    )
    if current_user_principal is not None:
        if isinstance(current_user_principal, list) or isinstance(current_user_principal, tuple):
            for base in current_user_principal:
                yield webdav.xml_node(
                    '{DAV:}href',
                    base.rstrip('/') + '/' + request.user.username + '/'
                )
        else:
            yield webdav.xml_node(
                '{DAV:}href',
                current_user_principal.rstrip(
                    '/') + '/' + request.user.username + '/'
            )


def prop_dav_current_user_privilege_set(dav, request, resource):
    write = webdav.xml_node('{DAV:}privilege')
    write.append(webdav.xml_node('{DAV:}all'))
    write.append(webdav.xml_node('{DAV:}read'))
    write.append(webdav.xml_node('{DAV:}write'))
    write.append(webdav.xml_node('{DAV:}write-properties'))
    write.append(webdav.xml_node('{DAV:}write-content'))
    return write


def prop_dav_acl(dav, request, resource):
    ace = webdav.xml_node('{DAV:}ace')
    ace_principal = webdav.xml_node('{DAV:}principal')
    ace_principal.append(webdav.xml_node('{DAV:}all'))
    # principals = prop_dav_current_user_principal(dav, request, resource)
    # for principal in principals:
    #    ace_principal.append(principal)
    ace.append(ace_principal)
    grant = webdav.xml_node('{DAV:}grant')
    privilege = webdav.xml_node('{DAV:}privilege')
    privilege.append(webdav.xml_node('{DAV:}write'))
    grant.append(privilege)
    ace.append(grant)
    return ace


def prop_dav_owner(dav, request, resource):
    return prop_dav_current_user_principal(dav, request, resource)


webdav.register_prop(
    '{DAV:}resourcetype',
    prop_dav_resourcetype,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}getcontentlength',
    prop_dav_getcontentlength,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}getetag',
    prop_dav_getetag,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}getcontenttype',
    prop_dav_getcontenttype,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}getlastmodified',
    prop_dav_getlastmodified,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}creationdate',
    prop_dav_creationdate,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}current-user-principal',
    prop_dav_current_user_principal,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}principal-URL',
    prop_dav_current_user_principal,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}current-user-privilege-set',
    prop_dav_current_user_privilege_set,
    webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}acl',
    prop_dav_acl,
    webdav.exceptions.Forbidden)

# webdav.register_prop(
#     '{DAV:}sync-token',
#     prop_dav_getetag,
#     webdav.exceptions.Forbidden)

webdav.register_prop(
    '{DAV:}owner',
    prop_dav_owner,
    webdav.exceptions.Forbidden)
