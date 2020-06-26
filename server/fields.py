import copy
from OpenSSL import crypto
from django import forms
from django.template.defaultfilters import filesizeformat
from django.utils.translation import ugettext_lazy as _
from django.conf import settings


class CertFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        self.max_upload_size = kwargs.pop('max_upload_size', None)
        if not self.max_upload_size:
            self.max_upload_size = settings.MAX_UPLOAD_SIZE
        super(CertFileField, self).__init__(*args, **kwargs)

    def clean(self, *args, **kwargs):
        data = super(CertFileField, self).clean(*args, **kwargs)

        if data.name.split('.')[-1] != 'pem':
            raise forms.ValidationError(_('Certificate must be in PEM format'))
        if data.size > self.max_upload_size:
            raise forms.ValidationError(_('File size must be under %s. Current file size is %s.') % (filesizeformat(self.max_upload_size), filesizeformat(data.size)))

        data_copy = copy.deepcopy(data)
        bin_data = data_copy.read()
        try:
            crypto.load_certificate(crypto.FILETYPE_PEM, bin_data)
        except:
            raise forms.ValidationError(_('File does not contain certificate.'))

        try:
            crypto.load_privatekey(crypto.FILETYPE_PEM, bin_data)
        except:
            raise forms.ValidationError(_('File does not contain private key'))

        return data
