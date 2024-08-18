from datetime import datetime

from django.utils import timezone
from icalendar import Calendar, Todo, vDatetime, vText


class TodoData:
    def __init__(self, summary: str, due: datetime = None, completed: datetime = None):
        self.summary = summary
        self.due = due
        self.completed = completed


def parse_todo(ics: bytes) -> TodoData:
    calendar = Calendar.from_ical(ics)
    for component in calendar.walk():
        if isinstance(component, Todo):
            completed = None
            if component.get('completed'):
                completed = component.get('completed').dt
            due = None
            if component.get('due'):
                due = component.get('due').dt

            return TodoData(str(component.get('summary')), due, completed)

    raise "Could not find todo."


def create_todo(uid: str, todoItem: TodoData) -> bytes:
    todo = Todo()
    todo['uid'] = uid
    todo['created'] = vDatetime(timezone.now())
    todo['summary'] = vText(todoItem.summary)
    todo['last-modified'] = vDatetime(timezone.now())

    if todoItem.due:
        todo['due'] = vDatetime(todoItem.due)

    if todoItem.completed:
        todo['completed'] = vDatetime(todoItem.completed)
        todo['status'] = 'COMPLETED'
    else:
        todo['status'] = 'NEEDS-ACTION'

    calendar = Calendar()
    calendar.add_component(todo)
    return calendar.to_ical()


def change_todo(ics: bytes, todoItem: TodoData) -> bytes:
    calendar = Calendar.from_ical(ics)

    for component in calendar.walk():
        if isinstance(component, Todo):
            todo = component
            todo['summary'] = vText(todoItem.summary)
            todo['last-modified'] = vDatetime(timezone.now())

            if todoItem.due:
                todo['due'] = vDatetime(todoItem.due)
            else:
                if todo.get('due'):
                    del todo['due']
            if todoItem.completed:
                todo['completed'] = vDatetime(todoItem.completed)
                todo['status'] = 'COMPLETED'
            else:
                if todo.get('completed'):
                    del todo['completed']
                todo['status'] = 'NEEDS-ACTION'

            return todo.to_ical()
