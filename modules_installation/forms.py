from modules_installation.fields import ModuleFileField
from server.forms import BaseForm


class UploadModuleFileForm(BaseForm):
    file = ModuleFileField(max_upload_size=512000)  # 500KB