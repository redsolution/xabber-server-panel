import base64
from django import forms
import re

from django.contrib.auth.models import Permission

from api.forms import AuthorizedApiForm
from api.utils import file_size_validator, file_extension_validator
from .models import User, Group, GroupMember, VirtualHost
from .utils import validate_jid
from server.utils import update_ejabberd_config


class RegisterUserForm(AuthorizedApiForm):
    api_method = 'create_user'

    username = forms.CharField(
        max_length=100,
        required=True,
        label='Username *',
        widget=forms.TextInput(attrs={'placeholder': 'Username', 'autofocus': ''})
    )
    host = forms.ChoiceField(
        required=True,
        widget=forms.Select()
    )
    password = forms.CharField(
        max_length=50,
        required=True,
        label='Password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )
    nickname = forms.CharField(
        max_length=100,
        required=False,
        label='Nickname',
        help_text="Nickname will be seen to user's contact.",
        widget=forms.TextInput(attrs={'placeholder': 'John Doe'})
    )
    first_name = forms.CharField(
        max_length=100,
        required=False,
        label='First name',
        help_text="Permitted symbols are a..z, 0..9, dots and underscores.",
        widget=forms.TextInput(attrs={'placeholder': 'John'})
    )
    last_name = forms.CharField(
        max_length=100,
        required=False,
        label='Last name',
        help_text="Permitted symbols are a..z, 0..9, dots and underscores.",
        widget=forms.TextInput(attrs={'placeholder': 'Doe'})
    )
    photo = forms.FileField(
        required=False,
        label='User avatar',
        help_text="GIF, PNG or JPG, 96x96 px or more."
    )
    is_admin = forms.BooleanField(
        required=False,
        label='Administrator',
        help_text="Promote user as admin"
    )

    def __init__(self, *args, **kwargs):
        self.vhosts = kwargs.pop('vhosts', None)
        super(RegisterUserForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
        if self.vhosts:
            self.fields['host'].choices = [(o.name, "@" + o.name)
                                           for o in self.vhosts]
        self.fields['photo'].widget.attrs['class'] = 'custom-file-input'
        self.fields['is_admin'].widget.attrs['class'] = 'form-check-input'

    def clean_photo(self):
        if self.cleaned_data.get('photo'):
            photo_file = self.cleaned_data['photo']
            file_size_validator(photo_file)
            file_extension = file_extension_validator(photo_file)
            self.cleaned_data['vcard_photo'] = {
                "type": "image/{}".format(file_extension),
                "binval": base64.b64encode(photo_file.read())
            }
        else:
            self.cleaned_data['photo'] = None
            self.cleaned_data['vcard_photo'] = {"type": "", "binval": ""}
        return self.cleaned_data['photo']

    def before_clean(self):
        if self.cleaned_data['username'].lower() == 'all':
            self.add_error('username', 'This username is forbidden.')
        vcard = dict()
        vcard['nickname'] = self.cleaned_data['nickname']
        vcard['n'] = {'given': self.cleaned_data['first_name'],
                      'family': self.cleaned_data['last_name']}
        vcard['photo'] = self.cleaned_data.pop('vcard_photo')
        self.cleaned_data['vcard'] = vcard
        regex = re.compile(r'^[a-zA-Z0-9$@$!%*?&#^-_. +]+$')
        if not regex.match(self.cleaned_data['username']):
            self.add_error('username', 'This username contains unsupported characters.')
        self.cleaned_data['username'] = self.cleaned_data['username'].lower()
        return self.cleaned_data

    def after_clean(self, cleaned_data):
        cleaned_data.pop('vcard')
        self.new_user = User.objects.create(**cleaned_data)
        if cleaned_data['is_admin'] is True:
            update_ejabberd_config()


class UnregisterUserForm(AuthorizedApiForm):
    api_method = 'unregister_user'

    username = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.HiddenInput(),
    )
    host = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.HiddenInput(),
    )

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username', None)
        self.host = kwargs.pop('host', None)
        super(UnregisterUserForm, self).__init__(*args, **kwargs)

    def before_clean(self):
        username = self.cleaned_data['username']
        host = self.cleaned_data['host']
        has_error = False
        if self.username and self.host:
            if self.username == username and self.host == host:
                self.add_error(None, 'You cannot delete yourself.')
                has_error = True
        user = User.objects.filter(username=username, host=host)
        if user.exists():
            user = user[0]
            if user.is_admin:
                if User.objects.filter(is_admin=True).count() == 1:
                    self.add_error(None, 'You cannot delete the last server admin.')
                    has_error = True
        if not has_error:
            groups = GroupMember.objects.filter(username=username, host=host)
            for group in groups:
                self.user.api.srg_user_del_api(data={
                    'user': username,
                    'host': host,
                    'group': group.group.group,
                    'grouphost': group.group.host
                })
            groups.delete()

    def after_clean(self, cleaned_data):
        user = User.objects.filter(username=cleaned_data['username'],
                                   host=cleaned_data['host'])
        if user.exists():
            if user[0].is_admin:
                user.delete()
                update_ejabberd_config()
            else:
                user.delete()


class EditUserVcardForm(RegisterUserForm):
    api_method = 'edit_user_vcard'

    def __init__(self, *args, **kwargs):
        super(EditUserVcardForm, self).__init__(*args, **kwargs)
        self.fields['username'].widget = forms.HiddenInput()
        self.fields['host'].widget = forms.HiddenInput()
        self.fields['photo'].widget.attrs['class'] = 'custom-file-input'
        self.fields.pop('password')

    def after_clean(self, cleaned_data):
        cleaned_data.pop('vcard')
        try:
            user = User.objects.get(username=cleaned_data['username'],
                                    host=cleaned_data['host'])
            user.nickname = cleaned_data['nickname']
            user.first_name = cleaned_data['first_name']
            user.last_name = cleaned_data['last_name']
            user.photo = cleaned_data['photo']
            user.save()
        except User.DoesNotExist:
            pass


class ChangeUserPasswordForm(AuthorizedApiForm):
    api_method = 'change_password_api'

    password = forms.CharField(
        max_length=50,
        required=True,
        label='Password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )

    confirm_password = forms.CharField(
        max_length=50,
        required=True,
        label='Confirm password *',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Confirm password'})
    )

    def __init__(self, *args, **kwargs):
        self.user_to_change = kwargs.pop('user_to_change', None)
        super(ChangeUserPasswordForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def before_clean(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        if password and confirm_password and password == confirm_password:
            self.cleaned_data.pop('password')
            self.cleaned_data.pop('confirm_password')
            self.cleaned_data['newpass'] = password
        else:
            self.add_error(None, 'Passwords do not match.')
        self.cleaned_data['user'] = self.user_to_change.username
        self.cleaned_data['host'] = self.user_to_change.host


GROUP_SUBSCRIBER_ALL = 'all'
GROUP_SUBSCRIBER_SELF = 'self'
GROUP_SUBSCRIBER_CUSTOM = 'custom'
GROUP_SUBSCRIBERS_CHOICE = [
    (GROUP_SUBSCRIBER_ALL, GROUP_SUBSCRIBER_ALL),
    (GROUP_SUBSCRIBER_SELF, GROUP_SUBSCRIBER_SELF),
    (GROUP_SUBSCRIBER_CUSTOM, GROUP_SUBSCRIBER_CUSTOM),
]


class CreateGroupForm(AuthorizedApiForm):
    api_method = 'create_group'

    group = forms.CharField(
        max_length=100,
        required=True,
        label='Circle',
        widget=forms.TextInput(attrs={'placeholder': 'Circle identifier', 'autofocus': ''})
    )
    host = forms.ChoiceField(
        required=True,
        widget=forms.Select()
    )
    name = forms.CharField(
        max_length=100,
        required=True,
        label='Name',
        widget=forms.TextInput(attrs={'placeholder': 'Name'})
    )
    description = forms.CharField(
        required=False,
        label='Description',
        widget=forms.Textarea(attrs={'rows': 4})
    )
    displayed_groups = forms.ChoiceField(
        label='Subscribers',
        widget=forms.Select(),
        choices=GROUP_SUBSCRIBERS_CHOICE,
        required=False)

    def __init__(self, *args, **kwargs):
        self.vhosts = kwargs.pop('vhosts', None)
        super(CreateGroupForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'
        if self.vhosts:
            self.fields['host'].choices = [(o.name, "@" + o.name)
                                           for o in self.vhosts]

    def clean_displayed_groups(self):
        if self.cleaned_data['displayed_groups'] == GROUP_SUBSCRIBER_ALL:
            return 'all'
        elif self.cleaned_data['displayed_groups'] == GROUP_SUBSCRIBER_SELF:
            return self.cleaned_data['group']
        else:
            return ''

    def before_clean(self):
        if self.cleaned_data['group'].lower() == 'all':
            self.add_error('group', 'This circle name is forbidden.')
        regex = re.compile(r'^[a-zA-Z0-9$@$!%*?&#^-_. +]+$')
        if not regex.match(self.cleaned_data['group']):
            self.add_error('group', 'This circle name contains unsupported characters.')
        elif Group.objects\
                .filter(group=self.cleaned_data['group'],
                        host=self.cleaned_data['host'])\
                .exists():
            self.add_error(None, 'Circle with this name and host already exist.')

    def after_clean(self, cleaned_data):
        self.new_group = Group.objects.create(**cleaned_data)


class EditGroupForm(CreateGroupForm):
    displayed_groups = forms.CharField(
        required=False,
        label='Visible circles',
        widget=forms.Textarea(attrs={'rows': 4}),
        help_text="Enter circle names separated by ; or , signs."
    )

    def __init__(self, *args, **kwargs):
        super(EditGroupForm, self).__init__(*args, **kwargs)
        self.fields['group'].widget = forms.HiddenInput()
        self.fields['host'].widget = forms.HiddenInput()

    def clean_displayed_groups(self):
        return self.cleaned_data['displayed_groups']\
            .replace(';', '\\n')\
            .replace(',', '\\n')

    def before_clean(self):
        pass

    def after_clean(self, cleaned_data):
        try:
            group = Group.objects.get(group=cleaned_data['group'],
                                      host=cleaned_data['host'])
            group.name = cleaned_data['name']
            group.description = cleaned_data['description']
            group.displayed_groups = cleaned_data['displayed_groups']
            group.save()

            group_members = GroupMember.objects.filter(group=group)
            for item in group_members:
                add_all_users_data = {
                    'user': item.username,
                    'host': item.host,
                    'group': group.group,
                    'grouphost': group.host
                }
                self.api.srg_user_add_api(data=add_all_users_data)
        except Group.DoesNotExist:
            pass


class AddGroupMemberForm(AuthorizedApiForm):
    api_method = 'srg_user_add_api'

    member = forms.CharField(
        max_length=256,
        required=True,
        label='Member',
        widget=forms.TextInput(attrs={'placeholder': 'username@server'})
    )

    def clean_member(self):
        member = self.cleaned_data.get('member').strip()
        jid_validation = validate_jid(member)
        if not jid_validation["success"]:
            raise forms.ValidationError(jid_validation["error_message"])
        return member

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super(AddGroupMemberForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def before_clean(self):
        if self.cleaned_data.get('member'):
            member = self.cleaned_data.pop('member').strip()
            self.cleaned_data['user'] = member.split('@')[0]
            self.cleaned_data['host'] = member.split('@')[1]
            if not VirtualHost.objects.filter(name=self.cleaned_data['host']).exists():
                self.add_error('member', "Can`t add member from external server")
        self.cleaned_data['group'] = self.group.group
        self.cleaned_data['grouphost'] = self.group.host

    def after_clean(self, cleaned_data):
        self.group.groupmember_set.get_or_create(username=cleaned_data['user'],
                                                 host=cleaned_data['host'])


class DeleteGroupMemberForm(AddGroupMemberForm):
    api_method = 'srg_user_del_api'

    def __init__(self, *args, **kwargs):
        super(DeleteGroupMemberForm, self).__init__(*args, **kwargs)
        self.fields['member'].widget = forms.HiddenInput()

    def after_clean(self, cleaned_data):
        self.group.groupmember_set\
            .filter(username=cleaned_data['user'], host=cleaned_data['host'])\
            .delete()


class AddGroupAllMemberForm(AuthorizedApiForm):
    api_method = 'srg_user_add_api'

    host = forms.CharField(
        max_length=256,
        required=True,
    )

    def __init__(self, *args, **kwargs):
        self.group = kwargs.pop('group', None)
        super(AddGroupAllMemberForm, self).__init__(*args, **kwargs)

    def before_clean(self):
        self.cleaned_data['user'] = '@all@'
        self.cleaned_data['host'] = self.cleaned_data['host']
        self.cleaned_data['group'] = self.group.group
        self.cleaned_data['grouphost'] = self.group.host

    def after_clean(self, cleaned_data):
        self.group.groupmember_set.get_or_create(username='@all@',
                                                 host=cleaned_data['host'])


class DeleteGroupAllMemberForm(AddGroupAllMemberForm):
    api_method = 'srg_user_del_api'

    def after_clean(self, cleaned_data):
        self.group.groupmember_set.filter(username='@all@',
                                          host=cleaned_data['host'])\
            .delete()


class DeleteGroupForm(AuthorizedApiForm):
    api_method = 'delete_group'

    group = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.HiddenInput(),
    )
    host = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.HiddenInput(),
    )

    def after_clean(self, cleaned_data):
        Group.objects\
            .filter(group=cleaned_data['group'],
                    host=cleaned_data['host'])\
            .delete()
