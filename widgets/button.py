from django.forms import Widget


class Button(Widget):
    button_type = None
    button_label = None
    is_list_action = False

    template_name = "widgets/button.html"

    def __init__(self, attrs=None, label=None, is_list_action=False):
        self.is_list_action = is_list_action
        if attrs is not None:
            attrs = attrs.copy()
            self.button_type = attrs.pop("type", self.button_type)
            self.button_label = attrs.pop("label", self.button_label)

        if label is not None:
            self.button_type = label

        super().__init__(attrs)

        if self.button_type is None:
            self.button_type = "button"

    def get_context(self, name, value, attrs):
        if attrs is not None:
            attrs = attrs.copy()
            self.button_type = attrs.pop("type", self.button_type)
            self.button_label = attrs.pop("label", self.button_label)

        context = super().get_context(name, value, attrs)
        context["widget"]["type"] = self.button_type
        context["widget"]["label"] = self.button_label
        context["widget"]["is_list_action"] = self.is_list_action
        return context


class ListActionButton(Button):
    def __init__(self, attrs=None, label=None):
        super().__init__(attrs, label, True)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        context["widget"]["type"] = 'button'
        return context
