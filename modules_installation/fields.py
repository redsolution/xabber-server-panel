from django import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.conf import settings

class ModuleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        self.max_upload_size = kwargs.pop('max_upload_size', None)
        if not self.max_upload_size:
            self.max_upload_size = settings.MAX_UPLOAD_SIZE
        super(ModuleFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(ModuleFileField, self).clean(*args, **kwargs)

        if data.name.split('.')[-1] != 'gz' and data.name.split('.')[-2] != 'tar':
            raise forms.ValidationError(_('Plugin must be in TAR.GZ format'))
        if data.size > self.max_upload_size:
            raise forms.ValidationError(_('File size must be under %s. Current file size is %s.') % (filesizeformat(self.max_upload_size), filesizeformat(data.size)))

        return data