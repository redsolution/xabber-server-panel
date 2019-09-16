from django import forms


class InstallerForm(forms.Form):
    STEP_1 = 'XMPP host'
    STEP_2 = 'Admin settings'
    STEP_3 = 'Database settings'
    STEP_4 = 'Installation'

    xmpp_host = forms.CharField(
        max_length=128,
        required=False,
        label='XMPP host',
        widget=forms.TextInput(attrs={'placeholder': 'example.com'})
    )
    admin_username = forms.CharField(
        max_length=100,
        required=False,
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': 'admin'})
    )
    admin_password = forms.CharField(
        max_length=100,
        required=False,
        label='Password',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )
    db_host = forms.CharField(
        max_length=100,
        required=False,
        label='Database server name',
        widget=forms.TextInput(attrs={'placeholder': 'localhost'})
    )
    db_name = forms.CharField(
        max_length=100,
        required=False,
        label='Database name',
        widget=forms.TextInput(attrs={'placeholder': 'xabberserver'})
    )
    db_user = forms.CharField(
        max_length=100,
        required=False,
        label='Database user',
        widget=forms.TextInput(attrs={'placeholder': 'admin'})
    )
    db_user_pass = forms.CharField(
        max_length=100,
        required=False,
        label='Database user password',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )

    def __init__(self, *args, **kwargs):
        self.step = kwargs.pop('step')
        super(InstallerForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def validate_step1(self):
        xmpp_host = self.data.get('xmpp_host', None)
        if not xmpp_host:
            self.add_error('xmpp_host', 'This field is required.')

    def validate_step2(self):
        self.validate_step1()

        admin_username = self.data.get('admin_username', None)
        if not admin_username:
            self.add_error('admin_username', 'This field is required.')

        admin_password = self.data.get('admin_password', None)
        if not admin_password:
            self.add_error('admin_password', 'This field is required.')

    def validate_step3(self):
        self.validate_step2()

        db_host = self.data.get('db_host', None)
        if not db_host:
            self.add_error('db_host', 'This field is required.')

        db_name = self.data.get('db_name', None)
        if not db_name:
            self.add_error('db_name', 'This field is required.')

        db_user = self.data.get('db_user', None)
        if not db_user:
            self.add_error('db_user', 'This field is required.')

    def clean(self):
        if self.step == self.STEP_1:
            self.validate_step1()
        elif self.step == self.STEP_2:
            self.validate_step2()
        else:
            self.validate_step3()


class QuickInstallerModeForm(forms.Form):
    STEP_1 = 'Admin settings'
    STEP_2 = 'Installation'

    admin_username = forms.CharField(
        max_length=100,
        required=False,
        label='Username',
        widget=forms.TextInput(attrs={'placeholder': 'admin'})
    )
    admin_password = forms.CharField(
        max_length=100,
        required=False,
        label='Password',
        widget=forms.PasswordInput(render_value=True, attrs={'placeholder': 'Password'})
    )

    def validate_step(self):

        admin_username = self.data.get('admin_username', None)
        if not admin_username:
            self.add_error('admin_username', 'This field is required.')

        admin_password = self.data.get('admin_password', None)
        if not admin_password:
            self.add_error('admin_password', 'This field is required.')

    def validate_stored_data(self):
        virtual_host = self.stored_data.get('virtual_host', None)
        if not virtual_host:
            self.add_error(None, 'Invalid stored value for xmpp host')
        db_host = self.stored_data.get('db_host', None)
        if not db_host:
            self.add_error(None, 'Invalid stored value for database host')
        db_name = self.stored_data.get('db_name', None)
        if not db_name:
            self.add_error(None, 'Invalid stored value for database name')
        db_user = self.stored_data.get('db_user', None)
        if not db_user:
            self.add_error(None, 'Invalid stored value for database user')
        db_password = self.stored_data.get('db_password', None)
        if not db_password:
            self.add_error(None, 'Invalid stored value for database user password')

    def __init__(self, *args, **kwargs):
        self.step = kwargs.pop('step')
        self.stored_data = kwargs.pop('stored_data')
        super(QuickInstallerModeForm, self).__init__(*args, **kwargs)
        for visible in self.visible_fields():
            visible.field.widget.attrs['class'] = 'form-control'

    def clean(self):
        self.validate_step()
        self.validate_stored_data()
        self.cleaned_data["xmpp_host"] = self.stored_data["virtual_host"]
        self.cleaned_data["db_host"] = self.stored_data["db_host"]
        self.cleaned_data["db_name"] = self.stored_data["db_name"]
        self.cleaned_data["db_user"] = self.stored_data["db_user"]
        self.cleaned_data["db_user_pass"] = self.stored_data["db_password"]
        if self.stored_data["http_host"]:
            self.cleaned_data["HTTP_HOST"] = self.stored_data["http_host"]
