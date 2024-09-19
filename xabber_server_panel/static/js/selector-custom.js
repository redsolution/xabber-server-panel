$(function () {

    //Selector widget
    let selector = $('.selector-custom-js');
    selector.each(function(index, select) {
        let selectorFrom = $(select).find('.selector-custom-from');
        let selectorTo = $(select).find('.selector-custom-to');

        let selectorFilterFrom = $(select).find('.selector-custom-filter-from');
        let selectorFilterTo = $(select).find('.selector-custom-filter-to');

        let selectorAdd = $(select).find('.selector-custom-add');
        let selectorRemove = $(select).find('.selector-custom-remove');

        let selectorAddAll = $(select).find('.selector-custom-add-all');
        let selectorRemoveAll = $(select).find('.selector-custom-remove-all');

        let selectorResult = $(select).find('.selector-custom-result');

        //Function to update hidden fields with selected members
        function updateHiddenFields() {
            let selectorOptionTo = selectorTo.find('option');
            let values = selectorOptionTo.map(function() {
                return this.value;
            }).get();

            values.sort(function(a, b) {
                return parseInt(a) - parseInt(b);
            });

            selectorResult.val(values.join(','));
            selectorResult.trigger('change');
        };

        //Filter avaliable members
        selectorFilterFrom.on('input', function() {
            let filter = $(this).val().toLowerCase();
            selectorFrom.find('option').each(function() {
                let text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(filter));
            });
        });

        //Filter added members
        selectorFilterTo.on('input', function() {
            let filter = $(this).val().toLowerCase();
            selectorTo.find('option').each(function() {
                let text = $(this).text().toLowerCase();
                $(this).toggle(text.includes(filter));
            });
        });

        //Add selected members
        selectorAdd.on('click', function(e) {
            e.preventDefault();
            selectorFrom.find('option:selected').appendTo(selectorTo);
            updateHiddenFields(); //Update hidden fields after adding
        });

        //Remove selected members
        selectorRemove.on('click', function(e) {
            e.preventDefault();
            selectorTo.find('option:selected').appendTo(selectorFrom);
            updateHiddenFields(); //Update hidden fields after removal
        });

        //Choose all members at once
        selectorAddAll.on('click', function(e) {
            e.preventDefault();
            selectorFrom.find('option').appendTo(selectorTo);
            updateHiddenFields(); //Update hidden fields after adding all
        });

        //Remove all members at once
        selectorRemoveAll.on('click', function(e) {
            e.preventDefault();
            selectorTo.find('option').appendTo(selectorFrom);
            updateHiddenFields(); //Update hidden fields after removing all
        });

        //Double-click for quick adding and removing of members
        selectorFrom.on('dblclick', 'option', function() {
            $(this).appendTo(selectorTo);
            updateHiddenFields(); //Update hidden fields after double-click
        });

        selectorTo.on('dblclick', 'option', function() {
            $(this).appendTo(selectorFrom);
            updateHiddenFields(); //Update hidden fields after double-click
        });

        //Double-click for mobile
        selectorFrom.on('touchstart', 'option', function(event) {
            let now = new Date().getTime();
            let lastTouch = $(this).data('lastTouch') || now + 1;
            let delta = now - lastTouch;
                if (delta < 500 && delta > 0) {
                    $(this).trigger('dblclick');
                    $(this).data('lastTouch', null);
                } else {
                $(this).data('lastTouch', now);
            }
        });

        selectorTo.on('touchstart', 'option', function(event) {
            let now = new Date().getTime();
            let lastTouch = $(this).data('lastTouch') || now + 1;
            let delta = now - lastTouch;
                if (delta < 500 && delta > 0) {
                    $(this).trigger('dblclick');
                    $(this).data('lastTouch', null);
                } else {
                $(this).data('lastTouch', now);
            }
        });
    });

});