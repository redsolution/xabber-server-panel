$(function () {

    let url, page, data;
    function ajax_send(url, page='', data={}) {
        let ajax_url = url + page;

        $.get(ajax_url, data, function(data) {
            $('.list-js').html(data['html']);
            setCurrentUrl();
            setSort();
            checkChange();
            initTooltip();
        });
    };

    $('#host').on('change', function() {
        $(this).parents('.form-host-js').trigger('submit');
    });

    //Loader block
    let loader = '<div class="d-flex align-items-center justify-content-center position-absolute top-0 start-0 w-100 h-100 bg-body bg-opacity-75 z-3"><div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div></div>';

    $('.list-js').on('click', '.pagination a', function(e) {
        e.preventDefault();

        let url = $(this).parents('.list-js').data('url');

        //Add Loader
        $(this).parents('.list-js').find('.table-adaptive').append(loader);

        //Set sort data
        let data = {}
        $(this).parents('.list-js').find('.sort-js:checked').map((index, elem) => data[$(elem).attr('name')] = $(elem).val());

        ajax_send(url, $(this).attr('href'), data);
    });

    function setSort() {
        $('.sort-js').on('change', function(e) {
            e.preventDefault();

            let url = $(this).parents('.list-js').data('url');

            //Add Loader
            $(this).parents('.list-js').find('.table-adaptive').append(loader);

            //Set sort data
            let data = {}
            $(this).parents('.list-js').find('.sort-js:checked').map((index, elem) => data[$(elem).attr('name')] = $(elem).val());

            ajax_send(url, $(this).attr('href'), data);
        });
    };
    setSort();

    //Check dns records ajax
    function checkHost() {
        $('.check-records-js, .check-cert-js').on('click', function(e) {
            e.preventDefault();
            let $this = $(this);
            let url = $this.data('url');

            if ($this.hasClass('check-records-js')) {
                $this.find('.spinner-border').removeClass('d-none');
                $this.attr('disabled', true);
            }

            if ($this.hasClass('check-cert-js')) {
                $this.parents('.host-list-js').find('.table-adaptive').append(loader);
            }

            $.get(url, {}, function(data) {
                if ($this.hasClass('check-records-js')) {
                    $this.find('.spinner-border').addClass('d-none');
                    $this.attr('disabled', false);
                }

                $('.host-list-js').html(data);

                //Reinit functions
                initTooltip();

                //Reset check change
                checkChange();
                checkHost();
            });
        });
    };
    checkHost();

    //Separate logic for search
    let target, object;
    function search_ajax(url, $target=$('.search-list-js'), object='', page='') {
        let ajax_url = url + page;
        let query = $('.search-list-js').data('querystring');

        //Parse the query string into an object
        let queryParams = {};
        query.split('&').forEach(function (param) {
            var keyValue = param.split('=');
            if (keyValue[0] != 'page'){
                queryParams[keyValue[0]] = keyValue[1];
            }
        });

        //Create the data objec`t with query parameters
        let data = {
            'object': object,
            ...queryParams
        };

        $.get(ajax_url, data, function(data){
            $target.html(data['html']);
            setCurrentUrl();
            searchPagination();
        });
    };

    function searchPagination() {
        $('.search-pagination-js').on('click', '.pagination a', function(e) {
            e.preventDefault();

            //Add Loader
            $(this).parents('.search-pagination-js').find('.table-adaptive').append(loader);

            search_ajax(
                $('.search-list-js').data('url'),
                target=$(this).parents('.search-pagination-js'),
                object=$(this).parents('.search-pagination-js').data('object'),
                $(this).attr('href')
            );
        });
    };
    searchPagination()

    function setCurrentUrl() {
        //Get the current URL
        let currentUrl = window.location.href;

        //Create a URL object
        let urlObject = new URL(currentUrl);

        //Construct the URL with only the scheme and host
        let schemeAndHost = urlObject.origin;

        //Check if the content of the span tag is empty
        if ($('.current-url-js').length != 0) {
            if ($('.current-url-js').text().trim() === ''){
                //If it's empty, insert the current URL
                $('.current-url-js').text(schemeAndHost);
            }
        }

        //Check if the content of the span tag is empty
        if ($('.show-url-js').length != 0 ) {
            if ($('.show-url-js').data('link').trim() === '') {
                //If it's empty, insert the current URL
                $('.show-url-js').data('link', schemeAndHost);
            }
        }
    };
    setCurrentUrl();

    //Toggle search
    $('.header-search-icon').on('click', function () {
        $('.header-search-content').slideToggle();
    });

    //Add url to title
    $(document).on('click', '.show-url-js', function() {
        let url = $(this).data('link');
        let key = $(this).data('key');
        let fullLink = url + '/?rkey=' + key;

        $('.title-url-js').attr('href', fullLink).text(fullLink);
    });

    //Copy url
    $(document).on('click', '.copy-url-js', function() {
        let $temp = $("<div>");
        $("body").append($temp);
        $temp.attr("contenteditable", true)
            .html($('.title-url-js').html()).select()
            .on("focus", function() { document.execCommand('selectAll', false, null); })
            .focus();
        document.execCommand("copy");
        $temp.remove();
    });

    //Generate password on click
    function generatePassword() {
        let length = 10,
        charset = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
        res = '';
        for (let i = 0, n = charset.length; i < length; ++i) {
            res += charset.charAt(Math.floor(Math.random() * n));
        }
        return res;
    };
    $(document).on('click', '.generate-password-js', function() {
        $(this).parent().find('input').val(generatePassword());
        $(this).parent().find('input').trigger('change');
        return false;
    });

    //Init tooltips
    function initTooltip() {
        const tooltipTriggerItem = document.querySelector('[data-bs-toggle="tooltip"]');
        if ($(tooltipTriggerItem).length > 0) {
            const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
            const tooltipList = [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));
        }
    };
    initTooltip();

    //Show/hide reason with change user status
    $('#user_status').on('change', function() {
        let optionVal = $(this).val();
        if (optionVal == "BLOCKED") {
            $(this).parent().next().addClass('show');
        } else {
            $(this).parent().next().removeClass('show');
        }
    });

    //Change radio input with admin checkbox
    $('#is_admin').on('change', function() {
        if ($(this).prop('checked')) {
            $(this).parents('form').find('.list-group-item').each(function(index, item) {
                $(item).find('input[type="radio"]').first().prop('checked', true);
                $(item).find('input[type="radio"]').attr('disabled', true);
            });
        } else {
            $(this).parents('form').find('input[type="radio"]').attr('disabled', false);
        }
    });

    //Set Cookie
    function setCookie(name, value, options = {}) {
        options = {
            path: '/',
        };

        if (options.expires instanceof Date) {
            options.expires = options.expires.toUTCString();
        }

        let updatedCookie = encodeURIComponent(name) + "=" + encodeURIComponent(value);

        for (let optionKey in options) {
            updatedCookie += "; " + optionKey;
            let optionValue = options[optionKey];
            if (optionValue !== true) {
                updatedCookie += "=" + optionValue;
            }
        }

        document.cookie = updatedCookie;
    };

    //Switch theme
    const themeSwitch = document.getElementById('theme_switch');
    if ($(themeSwitch).length > 0) {
        themeSwitch.addEventListener('change', function () {
            if (themeSwitch.checked) {
                document.documentElement.setAttribute('data-bs-theme', 'dark');
                setCookie('theme', 'dark');
            } else {
                document.documentElement.setAttribute('data-bs-theme', 'light');
                setCookie('theme', 'light');
            }
        });
    };

    //Check change in form
    function checkChange() {
        let form = $('.check-change-js');
        form.each(function(index, item) {
            let origFormTextInputs = $(item).find(':input:not(:file):not(.nocheck-change-js)').serialize();
            let origFormFileInputs = $(item).find(':file').map(function() {
                return this.value;
            }).get().join(',');

            // Check for change in text inputs
            $(item).find(':input:not(:file)').on('change input', function() {
                if ($(item).find(':input:not(:file):not(.nocheck-change-js)').serialize() !== origFormTextInputs || $(item).find(':file').map(function() {
                    return this.value;
                }).get().join(',') !== origFormFileInputs) {
                    $(item).find('button[name="save"]').prop('disabled', false).removeClass('btn-secondary');
                } else {
                    $(item).find('button[name="save"]').prop('disabled', true).addClass('btn-secondary');
                }
            });

            // Check for change in file inputs
            $(item).find(':file').on('change', function() {
                let currentFormFileInputs = $(item).find(':file').map(function() {
                    return this.value;
                }).get().join(',');

                if ($(item).find(':input:not(:file)').serialize() !== origFormTextInputs || currentFormFileInputs !== origFormFileInputs) {
                    $(item).find('button[name="save"]').prop('disabled', false).removeClass('btn-secondary');
                } else {
                    $(item).find('button[name="save"]').prop('disabled', true).addClass('btn-secondary');
                }
            });
        });
    };
    checkChange();

    //Check change date/time input
    let input = $('.check-date-js');
    input.each(function(index, item) {
        let inputDate = $(item).find('input[type="date"]');
        let inputTime = $(item).find('input[type="time"]');
        if (inputDate.val().length != 0) {
            inputTime.prop('disabled', false).removeClass('text-body-tertiary');
            inputDate.removeClass('text-body-tertiary');
        }
        inputDate.on('change input', function() {
            if ($(this).val().length != 0) {
                inputTime.prop('disabled', false).removeClass('text-body-tertiary');
                $(this).removeClass('text-body-tertiary');
            } else {
                inputTime.prop('disabled', true).addClass('text-body-tertiary');
                $(this).addClass('text-body-tertiary');
            }
        });
    });

    //Reset form checkbox in modal
    const resetCheckboxModal = document.querySelectorAll('.reset-checkbox-modal-js');
    resetCheckboxModal.forEach((modal) => {
        modal.addEventListener('hidden.bs.modal', event => {
            let formCheckbox = $(modal).find('form').find('input[type="checkbox"]');
            formCheckbox.each(function(index, checkbox) {
                if (typeof $(checkbox).attr('data-checked') === "undefined") {
                    $(this).prop('checked', false);
                } else {
                    $(this).prop('checked', true);
                }
            });
            //Fix submit disabled
            formCheckbox.first().trigger('change');
        })
    });

    //Reset form selector in modal
    const resetSelectorModal = document.querySelectorAll('.reset-selector-custom-modal-js');
    resetSelectorModal.forEach((modal) => {
        modal.addEventListener('hidden.bs.modal', event => {
            $(modal).find('form')[0].reset();

            let selectorSelect = $(modal).find('form').find('select');
            $(selectorSelect).find('option').prop('selected', false).trigger('chosen:updated');

            let selectorTo = $(modal).find('.selector-custom-to');
            let selectorFrom = $(modal).find('.selector-custom-from');
            let selectorResult = $(modal).find('.selector-custom-result');

            selectorTo.find('option:not([data-selected])').appendTo(selectorFrom);
            selectorFrom.find('option[data-selected]').appendTo(selectorTo);

            selectorTo.find('option').show();
            selectorFrom.find('option').show();

            let selectorOptionTo = selectorTo.find('option');
            let values = selectorOptionTo.map(function() {
                return this.value;
            }).get();
            values.sort(function(a, b) {
                return parseInt(a) - parseInt(b);
            });
            selectorResult.val(values.join(','));
            selectorResult.trigger('change');
        })
    });

    //Add delete link to modal
    $(document).on('click', '[data-delete-href]', function() {
        let deleteName = $(this).data('delete-name');
        let deleteTarget = $(this).data('delete-target');
        let deleteHref = $(this).data('delete-href');
        let deleteTitle = deleteName + ' ' + deleteTarget;

        $('#delete_modal .modal-header .modal-title').find('span').text(deleteTitle);
        $('#delete_modal .modal-footer a').attr('href', deleteHref).find('span').text(deleteName);
    });

    //Add block link to form
    $(document).on('click', '[data-block-href]', function() {
        let blockHref = $(this).data('block-href');
        $('#block_user').find('form').attr('action', blockHref);
    });

    //Show/hidden password
    let password = $('.password');
    password.each(function(index, item) {
        let input = $(item).find('.password-input');
        let btn = $(item).find('.password-btn');
        $(input).on('change input', function() {
            if ($(this).val().length === 0) {
                $(item).removeClass('active');
            } else {
                $(item).addClass('active');
            }
        });
        $(btn).on('click', function() {
            if (!$(this).hasClass('active-show')) {
                $(input).prop("type", "text");
                $(this).addClass('active-show');
            } else {
                $(input).prop("type", "password");
                $(this).removeClass('active-show');
            }
        });
    });

    //Start server loading
    let startserverForm = $('.form-startserver-js');
    let startserverLoader = $('.loader-startserver-js');
    let startserverTarget = document.querySelector('#start_server');
    if ($(startserverTarget).length > 0) {
        let startserverModal = new bootstrap.Modal(startserverTarget, {});
        $(startserverForm).on('submit', function() {
            startserverModal.hide();
            startserverLoader.find('.spinner-border').removeClass('d-none');
        });
    };

    //Init suggestions dropdown
    function checkSuggestions($object) {
        let text = $object.val();
        let objects = $object.data('objects');
        let type = $object.data('type');
        let url = $object.data('url');
        let target = $object.data('target');

        let data = {
            'text': text,
            'objects': objects,
            'type': type,
        };

        $.get(url, data, function(data) {
            if (data['html']){
                $(`.${target}`).html(data['html']);
            }
        });
    };

    let suggestions = $('.suggestions-custom-js');
    suggestions.each(function(index, item) {
        let suggestionsInput = $(item).find('.suggestions-custom__input');
        let suggestionsList = $(item).find('.suggestions-custom__list');

        //Show suggestions dropdown
        let timeout;
        suggestionsInput.on('input', function(e) {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                checkSuggestions($(this));
                suggestionsList.addClass('active');
            }.bind(this), 500); // 0.5 sec timeout
        });

        //Close suggestions dropdown
        $(document).on('click', function(e) {
            if (!suggestionsInput.is(e.target) && suggestionsInput.has(e.target).length === 0 && !suggestionsList.is(e.target) && suggestionsList.has(e.target).length === 0) {
                suggestionsList.removeClass('active');
            }
        });
    });

    //Add value suggestions dropdown
    $(document).on('click', '.suggestions-custom__item', function(e) {
        $(this).parents('.suggestions-custom-js').find('.suggestions-custom__input').val($(this).text().trim());
        $(this).parents('.suggestions-custom-js').find('.suggestions-custom__list').removeClass('active');
    });

    //Follow select
    let followSelect = $('.follow-select-js');
    followSelect.each(function(index, item) {
        let select = $(item).find('select');
        let input = $(item).find('input');

        select.on('change', function() {
            if ($(this).val() === '') {
                input.removeClass('custom-disabled');
            } else {
                input.addClass('custom-disabled');
            }
            input.val($(this).val());
            input.trigger('change');
        });

        input.on('input', function() {
            select.prop('selectedIndex', 0);
        });
    });

    //Config log update
    if ($('.log-list-js').length > 0) {
        updateLogList();
        updateLogInterval();
        var logInterval;

        $('input[name=log_range]').click(function(e){
            updateLogInterval();
            console.log('log range updated');
        });
    };

    function updateLogList() {
        let url = $('.log-list-js').data('url');
        let form_data = $('.log-form-js').serializeArray();
        let data = {};

        for (let i = 0; i < form_data.length; i++)
            data[form_data[i].name] = form_data[i].value;

        $.get(url, data, function(returned_data){
            $('.log-list-js').html(returned_data);
            console.log('Log list updated');
        });
    };

     //Check if log-list-js block exists
    function updateLogInterval(){
        //Clear existing interval before setting a new one
        if (logInterval) {
            clearInterval(logInterval);
        }

        let range = $('input[name=log_range]:checked').val() || 60
        //Optional: Automatically update the log list every minute
        logInterval = setInterval(function() {
            updateLogList();
        }, range * 1000); //60000 milliseconds = 1 minute
    };

});