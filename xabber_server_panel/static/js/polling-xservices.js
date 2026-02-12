$(function () {

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