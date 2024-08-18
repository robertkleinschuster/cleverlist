from django.db import models
from django.contrib.auth.models import User, Group
from django.utils import timezone

import webdav
import webdav.exceptions
from lxml import etree

from shopping.models import Item
from todo.models import Task
import uuid
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from webdav.storage import FSStorage
from webdav.todo import change_todo, TodoData, create_todo


# Create your models here.
class Resource(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    parent = models.ForeignKey('Resource', on_delete=models.CASCADE, null=True, blank=True)
    task = models.OneToOneField(Task, on_delete=models.CASCADE, null=True, blank=True)
    shoppingitem = models.OneToOneField(Item, on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=255, db_index=True)
    collection = models.BooleanField(default=False, db_index=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    content_type = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    size = models.BigIntegerField(default=0)
    protected = models.BooleanField(default=False)

    # pretty ugly, but should help viewing the full names
    def __str__(self):
        parts = []
        parent = self.parent
        while True:
            if not parent:
                break
            parts.insert(0, Resource.objects.get(pk=parent.id).name)
            parent = parent.parent
        parts.append(self.name)
        return '/' + '/'.join(parts)

    def del_prop(self, dav, request, name):
        try:
            model_prop = self.prop_set.get(name=name)
            model_prop.delete()
        except Prop.DoesNotExist:
            # removing a non existent property is not an error
            pass

    def get_prop(self, dav, request, name):
        if name in webdav.props_get:
            value = webdav.props_get[name](dav, request, self)
            if value is not None:
                return value
            raise webdav.exceptions.Forbidden()

        try:
            model_prop = self.prop_set.get(name=name)
            if model_prop.is_xml:
                return etree.fromstring(model_prop.value)
            return model_prop.value
        except Prop.DoesNotExist:
            raise webdav.exceptions.NotFound()

    def set_prop(self, dav, request, name, value):
        if name in webdav.props_set:
            e = webdav.props_set[name](dav, request, self, value)
            if isinstance(e, Exception):
                raise e
        else:
            try:
                prop = self.prop_set.get(name=name)
            except Prop.DoesNotExist:
                prop = self.prop_set.create(name=name)

            if len(value):
                prop.value = '\n'.join(
                    [etree.tostring(children, pretty_print=True).decode('utf-8)')
                     for children
                     in value]
                )
                prop.is_xml = True
            elif value.text is not None:
                prop.value = value.text
                prop.is_xml = False

            prop.save()
        return self.get_prop(dav, request, name)

    @property
    def displayname(self):
        try:
            prop = self.prop_set.get(name='{DAV:}displayname')
            return prop.value
        except:
            return ''

    @property
    def username(self) -> str:
        if self.user is None:
            return 'shared'
        return self.user.get_username()

    @property
    def storage_dir(self) -> str:
        if self.user is None:
            return 'shared'
        return str(self.user.pk)

    @property
    def progenitor(self):
        parent = self.parent
        while parent and parent.parent:
            parent = parent.parent
        return parent

    def properties(self, dav, request, requested_props):
        propstat = []
        for prop in requested_props:
            try:
                value = self.get_prop(dav, request, prop)
                status = '200 OK'
            except Exception as e:
                value = None
                if hasattr(e, 'status'):
                    status = e.status
                else:
                    status = '500 Internal Server Error'
            propstat.append((prop,) + (value, status))
        return propstat

    class Meta:
        unique_together = ('user', 'parent', 'name')


class Prop(models.Model):
    resource = models.ForeignKey(Resource, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, db_index=True)
    value = models.TextField(blank=True, null=True)
    is_xml = models.BooleanField(default=False)

    def __str__(self):
        return self.name

    class Meta:
        unique_together = ('resource', 'name')


@receiver(pre_delete, sender=Resource)
def delete_file(sender, instance: Resource, **kwargs):
    storage = FSStorage()
    storage.delete(instance)


@receiver(post_save, sender=Task)
def save_resource_for_task(sender, instance: Task, created, **kwargs):
    todoData = TodoData(
        summary=instance.name,
        due=instance.deadline,
        completed=instance.done
    )
    storage = FSStorage()
    if Resource.objects.filter(task=instance).exists():
        resource = Resource.objects.get(task=instance)
        ics = change_todo(storage.retrieve_string(resource), todoData)
        resource.size = len(ics)
        resource.save()
        storage.store_string(ics, resource)
        return

    if Resource.objects.filter(name="tasks").exists():
        parent = Resource.objects.get(name="tasks")
        uid = str(uuid.uuid4())
        ics = create_todo(uid, todoData)
        resource = Resource.objects.create(
            name=f'{uid}.ics',
            uuid=uid,
            parent=parent,
            user_id=parent.user_id,
            task=instance,
            content_type='text/calendar; charset=utf-8',
            size=len(ics),
        )
        storage.store_string(ics, resource)


@receiver(post_save, sender=Item)
def save_resource_for_shoppingitem(sender, instance: Item, created, **kwargs):
    completed = None
    if instance.in_cart:
        completed = timezone.now()

    todoData = TodoData(
        summary=str(instance),
        completed=completed
    )

    storage = FSStorage()
    if Resource.objects.filter(shoppingitem=instance).exists():
        resource = Resource.objects.get(shoppingitem=instance)
        ics = change_todo(storage.retrieve_string(resource), todoData)
        resource.size = len(ics)
        resource.save()
        storage.store_string(ics, resource)
        return

    if Resource.objects.filter(name="shoppingitems").exists():
        parent = Resource.objects.get(name="shoppingitems")
        uid = str(uuid.uuid4())
        ics = create_todo(uid, todoData)
        resource = Resource.objects.create(
            name=f'{uid}.ics',
            uuid=uid,
            parent=parent,
            user_id=parent.user_id,
            shoppingitem=instance,
            content_type='text/calendar; charset=utf-8',
            size=len(ics),
        )
        storage.store_string(ics, resource)
