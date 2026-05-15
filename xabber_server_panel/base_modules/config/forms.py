from django import forms
from .models import LDAPSettings, VirtualHost

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
