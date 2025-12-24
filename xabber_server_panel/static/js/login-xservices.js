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
                        reject(message);
                    } catch (e) {
                        const message = 'An error occurred: ' + xhr.responseText;
                        reject(message);
                    }
                }
            });
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

                const url = xservicesAuthModal.data('action');
                if (url){
                    const popup = window.open(
                        url,
                        '_blank',
                        'width=800,height=600,resizable=yes,scrollbars=yes'
                    );
                    updateModulesData();
                }
                else {
                    window.location.reload();
                }
                
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

    
    $(document).on('click','.purchase-module-js', function(e){
        e.preventDefault();
        const url = $(this).attr('href');

        const popup = window.open(
            url,
            '_blank',
            'width=800,height=600,resizable=yes,scrollbars=yes'
        );
    });

    // SERVICES POLLING
    function updateModulesData(){
        const loader_target = $('.table-adaptive');
        const data_target = $('.modules-data-js');

        addLoader(loader_target);
        if (data_target.length){
            const url = window.location.pathname;

            $.ajax({
                url: url, // Replace with your URL
                type: 'GET',
                success: function(response) {
                    let data = response.html
                    if (data){
                        data_target.html(data);
                    }
                    
                    deleteLoader(loader_target);
                },
                error: function(xhr, status, error) {
                    deleteLoader(loader_target);
                }
            });
        }
        else {
            window.location.reload()
        }
    }

    let previousData = null; // Store previous response

    function servicesPolling() {
        $.ajax({
            url: '/api/services_hash/', // Replace with your URL
            type: 'GET',
            success: function(response) {
                let services_hash = response.services_hash;
                // Compare with previous data
                if (previousData && services_hash && previousData != services_hash){
                    updateModulesData();
                }

                // Update previousData for next comparison
                previousData = services_hash;
            }
        });
    }

    setInterval(servicesPolling, 3000);
});
