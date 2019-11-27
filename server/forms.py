import re

from django import forms
from django.db import transaction

from virtualhost.models import User, VirtualHost
from .models import AuthBackend, LDAPSettings, LDAPServer


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

    ldap_server = forms.CharField(
        max_length=50,
        required=False,
        label='Server',
        widget=forms.TextInput(attrs={'placeholder': 'ldap1.example.org'})
    )
    ldap_port = forms.IntegerField(
        required=False,
        label='Port',
        widget=forms.TextInput(attrs={'placeholder': '389'})
    )
    ldap_rootdn = forms.CharField(
        max_length=100,
        required=False,
        label='Rootdn',
        widget=forms.TextInput(
            attrs={'placeholder': 'cn=Manager,dc=domain,dc=org'})
    )
    ldap_password = forms.CharField(
        max_length=50,
        required=False,
        label='Password',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': '********'})
    )

    def __init__(self, *args, **kwargs):
        super(ManageAuthBackendForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        self.curr_backend = AuthBackend.current()
        self.has_ldap_settings = LDAPSettings.has_saved_settings()
        self.fields['backend'].initial = self.curr_backend.name
        self.fields['backend'].choices = AuthBackend.BACKEND_CHOICES
        if self.has_ldap_settings:
            ldap_settings = LDAPSettings.current()
            self.fields['ldap_server'].initial = ldap_settings['server']
            self.fields['ldap_port'].initial = ldap_settings['port']
            self.fields['ldap_rootdn'].initial = ldap_settings['rootdn']
            self.fields['ldap_password'].initial = ldap_settings['password']

    def before_clean(self):
        if self.cleaned_data['backend'] == AuthBackend.BACKEND_LDAP:
            for field in self.cleaned_data.keys():
                if field.startswith('ldap_') and not self.cleaned_data[field]:
                    self.add_error(field, 'This field is required.')

    def after_clean(self, cleaned_data):
        with transaction.atomic():
            if cleaned_data['backend'] == AuthBackend.BACKEND_LDAP:
                LDAPSettings.create_or_update(cleaned_data)

            self.curr_backend.is_active = False
            self.curr_backend.save()

            self.new_backend = AuthBackend.objects.get(name=cleaned_data['backend'])
            self.new_backend.is_active = True
            self.new_backend.save()
