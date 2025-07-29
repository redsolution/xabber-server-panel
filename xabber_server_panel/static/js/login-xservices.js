$(function () {
    function form_ajax_send($form) {
        const url = $form.attr('action');
        const method = $form.attr('method') || 'POST';
        const data = $form.serialize();

        $.ajax({
            url: url,
            type: method,
            data: data,
            success: function(response) {
                console.log(response);
            },
            error: function(xhr, status, error) {
                // If response is JSON (try/catch to be safe)
                try {
                    const json = JSON.parse(xhr.responseText);
                    console.error('Response error:', json.message);
                } catch (e) {
                    // Not JSON, fallback
                    alert('An error occurred: ' + xhr.responseText);
                }
            }
        });
    }

    $('.xservices-form-js').on('submit', function(e) {
        e.preventDefault();
        form_ajax_send($(this));
    })
});