$(function () {

    let previousData = null;
    function servicesPolling() {
        $.ajax({
            url: '/api/services_hash/',
            type: 'GET',
            success: function(response) {
                let services_hash = response.services_hash;

                //Compare with previous data
                if (previousData && services_hash && previousData != services_hash){
                    updateModulesData();
                }

                //Update previousData for next comparison
                previousData = services_hash;
            }
        });
    }

    setInterval(servicesPolling, 3000);

});

//Services polling
function updateModulesData() {
    const data_target = $('.modules-data-js');

    addLoader(data_target);
    if (data_target.length) {
        const url = window.location.pathname;

        $.ajax({
            url: url,
            type: 'GET',
            success: function(response) {
                let data = response.html
                if (data) {
                    data_target.html(data);
                }
                
                deleteLoader(data_target);
            },
            error: function(xhr, status, error) {
                deleteLoader(data_target);
            }
        });
    }
    else {
        window.location.reload()
    }
}

export { updateModulesData };