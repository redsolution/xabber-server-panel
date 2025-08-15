//Stepper Clear
let disabledCloseModal = false;
function stepperClear(stepper) {
	stepper.find('.stepper__step').removeClass('completed active');
	stepper.find('.stepper__step[data-step="1"]').addClass('active');
	stepper.find('form').each(function(index, form) {
		form.reset();
		$(form).find('button[name="save"]').prop('disabled', true);
		$(form).find('.stepper__error').addClass('d-none').text('');
	});
};
$('.stepper-modal').on('hidden.bs.modal', function(event) {
	const $modal = $(this);
	if (disabledCloseModal) {
		event.preventDefault();
	} else {
		stepperClear($modal);
	}
});
$('.stepper-modal').on('hide.bs.modal', function(event) {
	if (disabledCloseModal) {
		event.preventDefault();
	}
});

//Stepper go to step
function stepperGoToStep(stepper, step) {
	const steps = stepper.find('.stepper__step');
	steps.removeClass('active completed');

	steps.each(function() {
		const currentStep = $(this);
		const stepNum = parseInt(currentStep.data('step'), 10);

		if (stepNum < step) {
			currentStep.addClass('completed');
		} else if (stepNum === step) {
			currentStep.addClass('active');
		}
	});
};