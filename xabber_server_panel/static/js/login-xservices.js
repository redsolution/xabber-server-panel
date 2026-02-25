import { updateModulesData } from './polling-xservices.js';

$(function () {
    //Function for modal (#xservices_auth)
    let xservicesAuthModal = $('#xservices_auth');
    let xservicesAuthModalBs = new bootstrap.Modal(xservicesAuthModal);
    $(document).on('click', '.xservices-auth-js', function(event) {
        event.preventDefault();

        $(xservicesAuthModal).data('action', $(this).attr('href'));
        $(xservicesAuthModal).data('redirect', $(this).data('redirect'));
        $(xservicesAuthModal).data('module-name', $(this).data('module-name'));

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

    function openPaymentPopup(url, redirect) {
        const loader_target = $('.modules-data-js');

        const popup = window.open(
            url,
            '_blank',
            'width=800,height=600,resizable=yes,scrollbars=yes'
        );

        let access_token = localStorage.getItem('access_token');
        if (access_token) {
            window.addEventListener('message', (event) => {
                if (event.data.type === 'REQUEST_TOKEN') {
                    event.source.postMessage(
                    {
                        type: 'TOKEN_RESPONSE',
                        token: access_token
                    },
                        event.origin
                    );
                }
            });
        }

        window.addEventListener('message', function (event) {
            if (event.data === 'payment_success') {
                if (redirect) {
                    if (loader_target) {
                        addLoader(loader_target);
                    }
                    setTimeout(() => {
                        window.location.assign(redirect);
                    }, 2000);
                    return
                }
                else window.location.reload();
            }
        });
    }

    function updateLicenseData(account){
        const licenseAccount = $('.license-account-js');
        const licenseConnect = $('.license-connect-js');

        if (account){
            licenseConnect.addClass('d-none');
            licenseAccount.removeClass('d-none');
            licenseAccount.find('span').html(account);
        }
        else {
            licenseConnect.removeClass('d-none');
            licenseAccount.addClass('d-none');
            licenseAccount.find('span').html('');
        }
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
                const loader_target = $('.modules-data-js');
                
                //Remove error messages
                currentStep.find('.stepper__error').addClass('d-none').text('');

                //Close modal
                disabledCloseModal = false;
                xservicesAuthModalBs.hide();

                const url = xservicesAuthModal.data('action');
                const redirect = xservicesAuthModal.data('redirect');
                const moduleName = xservicesAuthModal.data('module-name');

                //Save access token
                const access_token = response.access_token;
                localStorage.setItem('access_token', access_token);

                const purchased_modules = response.purchased_modules;
                if (purchased_modules && purchased_modules.includes(moduleName)) {
                    if (redirect) {
                        if (loader_target) {
                            addLoader(loader_target);
                        }
                        window.location.assign(redirect);
                        return
                    }
                    else window.location.reload();
                }
                if (url) {
                    openPaymentPopup(url, redirect);   
                }

                const account = response.account;

                updateModulesData();
                updateLicenseData(account);
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

    
    $(document).on('click','.modules-data-js', function(e){
        e.preventDefault();
        const url = $(this).attr('href');
        const redirect = $(this).data('redirect');

        openPaymentPopup(url, redirect);  
    });

    //Check internet connection
    document.addEventListener('click', async function(e) {
        const el = e.target.closest('.check-internet-connection');
        if (!el) return;

        const isOnline = navigator.onLine;

        let warningModal = $('#warning_modal');
        let warningModalBs = bootstrap.Modal.getInstance(warningModal[0]) || new bootstrap.Modal(warningModal[0]);
        let deleteModal = $('#delete_modal');
        let deleteModalBs = bootstrap.Modal.getInstance(deleteModal[0]) || new bootstrap.Modal(deleteModal[0]);

        if (!isOnline) {
            if (warningModal.length > 0) {
                //Open #warning_modal
                warningModal.find('.modal-body .alert').html('Internet connection is unavailable! Installed module data will not be updated. We recommend configuring your internet connection.')
                warningModalBs.show();

                //Check close and open #delete_modal
                warningModal[0].addEventListener('hidden.bs.modal', function() {
                    if (deleteModal.length > 0) {
                        deleteModalBs.show();
                    }
                }, { once: true });
            }
            return;
        } else {
            if (deleteModal.length > 0) {
                //Open #delete_modal
                deleteModalBs.show();
            }
        }
    }, true);
});
