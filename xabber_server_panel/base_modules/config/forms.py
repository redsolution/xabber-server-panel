from django import forms
from django.forms import modelformset_factory
from .models import LDAPSettings, VirtualHost, XmppComponent

from jid_validation.utils import validate_host


class LDAPSettingsForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = LDAPSettings

    server_list = forms.CharField(
        required=False,
        label='Server list',
        widget=forms.Textarea(
            attrs={
                'placeholder': 'ldap1.example.org\n'
                               'ldap2.example.org\n'
                               'ldap3.example.org'
            }
        ),
        help_text='Enter the each server name from a new line'
    )


class VirtualHostForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
        model = VirtualHost

    def clean_name(self):
        name = self.cleaned_data['name']

        # validate and normalize name
        result = validate_host(name)
        if result.get('success'):
            name = result.get('host')
        else:
            self.add_error('name', result.get('error_message'))

        return name


class AdvancedSettingsForm(forms.Form):
    mod_webhooks_url = forms.URLField(
        required=False,
        label='MOD_WEBHOOKS_URL'
    )
    mod_devices_enabled = forms.BooleanField(
        required=False,
        label='Enable mod_devices',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    mod_devices_devices_only = forms.BooleanField(
        required=False,
        label='Devices only',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    mod_devices_device_expiration_time = forms.IntegerField(
        required=False,
        min_value=0,
        label='Device expiration time',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )


class XmppComponentForm(forms.ModelForm):

    class Meta:
        model = XmppComponent
        fields = ('host', 'ip', 'port', 'password', 'enabled', 'privileged')
        widgets = {
            'host': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'max.example.com'}),
            'ip': forms.TextInput(attrs={'class': 'form-control'}),
            'port': forms.NumberInput(attrs={'class': 'form-control', 'min': 1, 'max': 65535}),
            'password': forms.PasswordInput(attrs={'class': 'form-control'}, render_value=True),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'privileged': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_host(self):
        name = self.cleaned_data['host']
        result = validate_host(name)
        if result.get('success'):
            return result.get('host')
        raise forms.ValidationError(result.get('error_message'))

    def clean_port(self):
        port = self.cleaned_data['port']
        if port > 65535:
            raise forms.ValidationError('Port must be between 1 and 65535.')
        return port


XmppComponentFormSet = modelformset_factory(
    XmppComponent,
    form=XmppComponentForm,
    extra=0,
)
