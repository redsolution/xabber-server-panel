$(function () {
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
                    // Add error messages
                    console.log(response.errors);
                }
                else {
                    window.location.reload();
                    // Add error messages
                    console.log('Module installed successfully.');
                } 
            }
        });
    }

    $('.xservices-login-js').on('submit', function (e) {
        e.preventDefault();
        // add loader 

        form_ajax_send($(this))
            .then(function (response) {
                // Go to next step

            })
            .catch(function (error) {
                // Add error messages
                console.log("Login step failed:", error);
            });

        // remove loader
        
    });

    $('.xservices-confirm-js').on('submit', function (e) {
        e.preventDefault();
        // add loader 

        form_ajax_send($(this))
            .then(function (response) {
                const url = $('#enter_token').data('action');
                upload_module(url);
            })
            .catch(function (error) {
                // Add error messages
                console.log("Confirmation step failed:", error);
            });

        // remove loader

    });

    $('.upload-module-js').click(function(e){
        e.preventDefault();
        // add loader

        const url = $(this).attr('href');
        upload_module(url);
    });
});
