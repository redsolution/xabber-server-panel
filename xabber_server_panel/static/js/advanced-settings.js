$(function () {
    let form = $('.advanced-settings-js');
    let modDevicesEnabled = $('#id_mod_devices_enabled');
    let modDevicesFields = $('#id_mod_devices_devices_only, [name="mod_devices_device_expiration_time"]');
    let componentList = $('.components-list-js');
    let componentTemplate = $('.component-empty-form-js');
    let totalComponentForms = $('#id_components-TOTAL_FORMS');
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

    form.on('change input', '.components-list-js :input', updateSaveButton);

    $('.add-component-js').on('click', function () {
        let index = parseInt(totalComponentForms.val(), 10);
        let row = componentTemplate.html().replace(/__prefix__/g, index);
        componentList.append(row);
        totalComponentForms.val(index + 1);
        updateSaveButton();
    });

    componentList.on('click', '.remove-component-js', function () {
        $(this).closest('.component-row-js').remove();
        updateSaveButton();
    });
});
