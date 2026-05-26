$(function () {
    let form = $('.advanced-settings-js');
    let modDevicesEnabled = $('#id_mod_devices_enabled');
    let modDevicesFields = $('#id_mod_devices_devices_only, [name="mod_devices_device_expiration_time"]');
    let initialFormState = form.find(':input:not(:file):not(.nocheck-change-js)').serialize();

    function updateSaveButton() {
        let changed = form.find(':input:not(:file):not(.nocheck-change-js)').serialize() !== initialFormState;
        form.find('button[name="save"]').prop('disabled', !changed).toggleClass('btn-secondary', !changed);
    }

    function updateModDevicesFields() {
        modDevicesFields.prop('disabled', !modDevicesEnabled.is(':checked'));
        updateSaveButton();
    }

    modDevicesEnabled.on('change', updateModDevicesFields);
    modDevicesFields.on('change input', updateSaveButton);
});