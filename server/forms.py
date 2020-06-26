import re

from ldap3 import Server, Connection, ALL

from django import forms
from .fields import CertFileField
from virtualhost.models import User, VirtualHost
from .models import LDAPSettings


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


class LDAPSettingsForm(BaseForm):
    ldap_vhost = forms.ChoiceField(
        required=False,
        label='Host',
        widget=forms.Select()
    )
    is_enabled = forms.BooleanField(
        required=False,
        label='Enable',
        initial=False
    )

    ldap_server_list = forms.CharField(
        required=False,
        label='Server list',
        help_text='Enter the each server name from a new line',
        widget=forms.Textarea(attrs={
            'placeholder': 'ldap1.example.org\n'
                           'ldap2.example.org\n'
                           'ldap3.example.org',
            'rows': 4,
            'hint': 'List of IP addresses or DNS names of your LDAP servers. '
                    'This option is required.'})
    )
    ldap_encrypt = forms.ChoiceField(
        choices=LDAPSettings.ENCRYPT_CHOICE,
        required=False,
        label='Encrypt',
        widget=forms.Select(attrs={
            'hint': 'Type of connection encryption to the LDAP server. '
                    'Allowed values are: none, tls. The value tls enables '
                    'encryption by using LDAP over SSL. Note that STARTTLS '
                    'encryption is not supported. The default value is: none.'
        })
    )
    ldap_tls_verify = forms.ChoiceField(
        choices=LDAPSettings.TLS_VERIFY_CHOICE,
        required=False,
        label='TLS verify',
        widget=forms.Select(attrs={
            'hint': 'This option specifies whether to verify LDAP server '
                    'certificate or not when TLS is enabled. When hard is '
                    'enabled ejabberd does not proceed if a certificate is '
                    'invalid. When soft is enabled ejabberd proceeds even if '
                    'check fails. The default is false which means no checks '
                    'are performed.'
        })
    )
    ldap_tls_cacertfile = forms.CharField(
        max_length=100,
        required=False,
        label='TLS cacertfile',
        widget=forms.TextInput(attrs={
            'hint': 'Path to file containing PEM encoded CA certificates. '
                    'This option is needed (and required) when TLS verification '
                    'is enabled.'
        })
    )
    ldap_tls_depth = forms.IntegerField(
        required=False,
        label='TLS depth',
        widget=forms.TextInput(attrs={
            'hint': 'Specifies the maximum verification depth when TLS '
                    'verification is enabled, i.e. how far in a chain of '
                    'certificates the verification process can proceed before '
                    'the verification is considered to fail. Peer '
                    'certificate = 0, CA certificate = 1, higher level CA '
                    'certificate = 2, etc. The value 2 thus means that a chain '
                    'can at most contain peer cert, CA cert, next CA cert, and '
                    'an additional CA cert. The default value is 1.'
        })
    )
    ldap_port = forms.IntegerField(
        required=False,
        initial=389,
        label='Port',
        widget=forms.TextInput(attrs={
            'hint': "Port to connect to your LDAP server. The default port is "
                    "389 if encryption is disabled; and 636 if encryption is "
                    "enabled. If you configure a value, it is stored in "
                    "ejabberd's database. Then, if you remove that value from "
                    "the configuration file, the value previously stored in "
                    "the database will be used instead of the default port."
        })
    )
    ldap_rootdn = forms.CharField(
        max_length=100,
        required=False,
        label='Rootdn',
        widget=forms.TextInput(attrs={
            'placeholder': 'cn=Manager,dc=domain,dc=org',
            'hint': "Bind DN. The default value is empty string '' which "
                    "means 'anonymous connection'."
        })
    )
    ldap_password = forms.CharField(
        max_length=50,
        required=False,
        label='Password',
        widget=forms.PasswordInput(render_value=True, attrs={
            'placeholder': '********',
            'hint': 'Bind password. The default value is is empty string.'
        })
    )
    ldap_deref_aliases = forms.ChoiceField(
        choices=LDAPSettings.DEFER_ALIASES_CHOICE,
        required=False,
        label='Defer aliases',
        widget=forms.Select(attrs={
            'hint': "Whether or not to dereference aliases. The default is "
                    "never."
        })
    )
    ldap_base = forms.CharField(
        max_length=100,
        required=False,
        label='Base',
        widget=forms.TextInput(attrs={
            'placeholder': 'ou=Users,dc=example,dc=org',
            'hint': 'LDAP base directory which stores users accounts. This '
                    'option is required.'
        })
    )
    ldap_uids = forms.CharField(
        required=False,
        label='UIDs',
        widget=forms.TextInput(attrs={
            'hint': "LDAP attribute which holds a list of attributes to use as "
                    "alternatives for getting the JID. The default attributes "
                    "are [{uid, %u}]. The attributes are of the form: "
                    "[{ldap_uidattr}] or [{ldap_uidattr, ldap_uidattr_format}]. "
                    "You can use as many comma separated attributes as needed."
        })
    )
    ldap_filter = forms.CharField(
        max_length=100,
        required=False,
        label='Filter',
        widget=forms.TextInput(attrs={
            'placeholder': '(&(objectClass=shadowAccount)(memberOf=Jabber Users))',
            'hint': 'LDAP filter. The default Filter value is: undefined. '
                    'Please, do not forget to close brackets and do not use '
                    'superfluous whitespaces. Also you must not use ldap_'
                    'uidattr attribute in filter because this attribute will '
                    'be substituted in LDAP filter automatically.'
        })
    )
    ldap_dn_filter = forms.CharField(
        max_length=100,
        required=False,
        label='DN filter',
        widget=forms.TextInput(attrs={
            'hint': "This filter is applied on the results returned by the "
                    "main filter. This filter performs additional LDAP lookup "
                    "to make the complete result. This is useful when you are "
                    "unable to define all filter rules in ldap_filter. You can "
                    "define %u, %d, %s and %D pattern variables in Filter: %u "
                    "is replaced by a user's part of a JID, %d is replaced by "
                    "the corresponding domain (virtual host), all %s variables "
                    "are consecutively replaced by values of FilterAttrs "
                    "attributes and %D is replaced by Distinguished Name. "
                    "By default ldap_dn_filter is undefined."
        })
    )

    LDAP_FIELDS_REQUIRED = ['ldap_server_list', 'ldap_port', 'ldap_base',
                            'ldap_vhost']
    LDAP_FIELDS = ['ldap_server_list', 'ldap_encrypt', 'ldap_tls_verify',
                   'ldap_tls_cacertfile', 'ldap_tls_depth', 'ldap_port',
                   'ldap_rootdn', 'ldap_password', 'ldap_deref_aliases',
                   'ldap_base', 'ldap_uids', 'ldap_filter', 'ldap_dn_filter',
                   'ldap_vhost', 'is_enabled']

    def init_ldap_vhost(self):
        self.fields['ldap_vhost'].choices = [
            (o.name, o.name) for o in self.vhosts]
        self.fields['ldap_vhost'].initial = self.vhost.name

    def init_ldap_attrs(self):
        ldap_conn = LDAPSettings.get(vhost=self.vhost)
        if not ldap_conn:
            return

        for field in self.LDAP_FIELDS:
            if hasattr(ldap_conn, field):
                self.fields[field].initial = getattr(ldap_conn, field)
            elif field == 'ldap_server_list':
                self.fields[field].initial = '\n'.join(
                    [s.server for s in ldap_conn.servers])

    def __init__(self, *args, **kwargs):
        self.vhosts = kwargs.pop('vhosts')
        self.vhost = kwargs.pop('vhost', self.vhosts[0])

        super(LDAPSettingsForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

        self.init_ldap_vhost()
        self.init_ldap_attrs()

    def check_required_fields(self):
        for field in list(self.cleaned_data.keys()):
            if field in self.LDAP_FIELDS_REQUIRED and \
                    not self.cleaned_data[field]:
                self.add_error(field, 'This field is required.')

    def check_ldap_conn(self):
        self.cleaned_data['ldap_server_list'] = \
            self.cleaned_data.get('ldap_server_list', '').splitlines()

        invalid_server_list = []
        for server_name in self.cleaned_data['ldap_server_list']:
            server = Server(server_name, get_info=ALL)
            conn = Connection(server)
            try:
                success = conn.bind()
            except Exception:
                invalid_server_list.append(server_name)
            else:
                if not success:
                    invalid_server_list.append(server_name)

        if invalid_server_list:
            self.add_error('ldap_server_list', 'Invalid server list: {}.'
                           .format(', '.join(invalid_server_list)))

    def clean_ldap_vhost(self):
        host = self.cleaned_data.get('ldap_vhost')
        return VirtualHost.objects.get(name=host)

    def before_clean(self):
        self.check_required_fields()
        self.check_ldap_conn()

    def after_clean(self, cleaned_data):
        data = {k: cleaned_data[k] for k in self.LDAP_FIELDS}
        LDAPSettings.create_or_update(data)


class DeleteCertFileForm(BaseForm):
    file = forms.CharField(
        max_length=255,
        required=True,
        widget=forms.HiddenInput(),
    )


class UploadCertFileForm(BaseForm):
    file = CertFileField(max_upload_size=102400)  # 100KB
