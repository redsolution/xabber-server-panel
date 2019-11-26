from django import forms
import re
from api.forms import AuthorizedApiForm

from virtualhost.models import User, VirtualHost, AuthBackend


class BaseForm(forms.Form):
    def __init__(self, *args, **kwargs):
        super(BaseForm, self).__init__(*args, **kwargs)

    def clean(self):
        self.before_clean()
        super(BaseForm, self).clean()
        if not self.errors:
            self.after_clean(self.cleaned_data)
        return self.cleaned_data

    def before_clean(self):
        pass

    def after_clean(self, cleaned_data):
        pass


class SelectAdminForm(BaseForm):
    api_method = 'srg_user_add_api'

    user = forms.CharField(
        max_length=256,
        required=True,
        label='User',
        widget=forms.TextInput(attrs={'placeholder': 'username@server'})
    )

    def clean_user(self):
        user = self.cleaned_data.get('user')
        return user

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop('action', None)
        super(SelectAdminForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def before_clean(self):
        if self.cleaned_data.get('user'):
            user = self.cleaned_data.pop('user')
            self.cleaned_data['user'] = user.split('@')[0]
            self.cleaned_data['host'] = user.split('@')[1]
            self.cleaned_data['action'] = self.action
            if self.action is 'delete':
                if User.objects.filter(is_admin=True).count() <= 1:
                    self.add_error(None, 'You cannot delete the last server admin.')

    def after_clean(self, cleaned_data):
        if cleaned_data['action'] is 'add':
            User.objects.filter(username=cleaned_data['user'],
                                host=cleaned_data['host']).update(is_admin=True)
        elif cleaned_data['action'] is 'delete':
            User.objects.filter(username=cleaned_data['user'],
                                host=cleaned_data['host']).update(is_admin=False)


class AddVirtualHostForm(BaseForm):
    api_method = 'srg_user_add_api'

    name = forms.CharField(
        max_length=256,
        required=True,
        label='Virtual host',
        widget=forms.TextInput(attrs={'placeholder': 'example.com'})
    )

    def clean_name(self):
        name = self.cleaned_data.get('name')
        return name

    def __init__(self, *args, **kwargs):
        super(AddVirtualHostForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def before_clean(self):
        regex = re.compile(r'^[a-zA-Z0-9$@$!%*?&#^-_. +]+$')
        if not regex.match(self.cleaned_data['name']):
            self.add_error('name', 'Virtual host name contains unsupported characters.')
        else:
            if VirtualHost.objects.filter(name=self.cleaned_data['name']).exists():
                self.add_error(None, 'Virtual host with this name already exist.')

    def after_clean(self, cleaned_data):
        self.new_vhost = VirtualHost.objects.create(**cleaned_data)


class DeleteVirtualHostForm(BaseForm):

    name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.HiddenInput(),
    )

    def before_clean(self):
        if VirtualHost.objects.all().count() == 1:
            self.add_error(None, 'You cannot delete the last virtual host.')

    def after_clean(self, cleaned_data):
        VirtualHost.objects \
            .filter(name=cleaned_data['name']) \
            .delete()


class ManageAuthBackendForm(BaseForm):

    backend = forms.ChoiceField(
        required=True,
        widget=forms.Select()
    )

    def __init__(self, *args, **kwargs):
        super(ManageAuthBackendForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        self.fields['backend'].choices = AuthBackend.BACKEND_CHOICES
        if AuthBackend.objects.filter(is_active=True).exists():
            self.curr_backend = self.curr_backend[0]
            self.fields['backend'].initial = self.curr_backend.name

    def after_clean(self, cleaned_data):
        self.curr_backend.is_active = False
        self.curr_backend.save()

        self.new_backend = AuthBackend.objects.get(name=cleaned_data['backend'])
        self.new_backend.is_active = True
        self.new_backend.save()
