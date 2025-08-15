$(function () {
	//Function for modal (#xservices_auth)
	let xservicesAuthModal = $('#xservices_auth');
	let xservicesAuthModalBs = new bootstrap.Modal(xservicesAuthModal);
	$(document).on('click', '.xservices-auth-js', function(event) {
		event.preventDefault();

		//Add action
		let url = $(this).attr('href');
		$(xservicesAuthModal).data('action', url);

		//Open modal
		xservicesAuthModalBs.show();
	});

    function getCookie(name) {
        const matches = document.cookie.match(new RegExp(
            "(?:^|; )" + name.replace(/([.$?*|{}()[\]\\/+^])/g, '\\$1') + "=([^;]*)"
        ));
        return matches ? decodeURIComponent(matches[1]) : undefined;
    }

    function form_ajax_send($form) {
        const url = $form.attr('action');
        const method = $form.attr('method') || 'POST';
        const data = $form.serialize();

        return new Promise((resolve, reject) => {
            $.ajax({
                url: url,
                type: method,
                data: data,
                success: function (response) {
                    console.log(response);
                    resolve(response);
                },
                error: function (xhr, status, error) {
                    try {
                        const json = JSON.parse(xhr.responseText);
                        const message = json.message;
                        console.log(message);
                        reject(message);
                    } catch (e) {
                        const message = 'An error occurred: ' + xhr.responseText;
                        console.log(message);
                        reject(message);
                    }
                }
            });
        });
    }

    function upload_module(url) {
        const csrfToken = getCookie('csrftoken');

        const data = {
            csrfmiddlewaretoken: csrfToken
        };

        $.ajax({
            url: url,
            type: 'POST',
            data: data,
            success: function (response) {
                if (response.errors.length){
                    //Add error messages
                    createMessage(response.errors, $('.message-js'), 'text-bg-danger');
                }
                else {
                    //Add success messages
                    createMessage('Module installed successfully', $('.message-js'), 'text-bg-success');

                    window.location.reload();
                } 
            }
        });
    }

    $('.xservices-login-js').on('submit', function (e) {
        e.preventDefault();

        let currentStep = $(this).parents('.stepper__step');

        //Add loader
        addLoader(currentStep.find('.stepper__content'));

        form_ajax_send($(this))
            .then(function (response) {
                //Remove error messages
                currentStep.find('.stepper__error').addClass('d-none').text('');

				//Step 2
				stepperGoToStep(xservicesAuthModal, 2);
            })
            .catch(function (error) {
                //Add error messages
                currentStep.find('.stepper__error').removeClass('d-none').text(error);
            })
            .finally(function () {
				//Remove Loader
				deleteLoader(currentStep.find('.stepper__content'));
            });
    });

    $('.xservices-confirm-js').on('submit', function (e) {
        e.preventDefault();

        let currentStep = $(this).parents('.stepper__step');

        //Add loader
        addLoader(currentStep.find('.stepper__content'));

		//Disabled close stepper modal
		disabledCloseModal = true;

        form_ajax_send($(this))
            .then(function (response) {
                //Remove error messages
                currentStep.find('.stepper__error').addClass('d-none').text('');

				//Close modal
				disabledCloseModal = false;
				xservicesAuthModalBs.hide();

                const url = $('#xservices_auth').data('action');
                upload_module(url);
            })
            .catch(function (error) {
                //Add error messages
                currentStep.find('.stepper__error').removeClass('d-none').text(error);
            })
            .finally(function () {
				//Remove Loader
				deleteLoader(currentStep.find('.stepper__content'));
            });
    });

    $('.upload-module-js').click(function(e){
        e.preventDefault();
        //Add loader
        addLoader($(this).parents('.table-adaptive'));

        const url = $(this).attr('href');
        upload_module(url);
    });
});
