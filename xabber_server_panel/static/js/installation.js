$(function () {

    $(document).on('click', '.installation-next', function(event) {
        let btnNext = $(this);
        let input = $(btnNext).parents('.installation-content').find('.installation-required');

        //Prevent double form submit
        let form = btnNext.parents('.installation-form');
        form.attr('disabled', true);

        let inputValue = input.filter(function() {
            return this.value === '';
        });

        if (inputValue.length) {
            event.preventDefault();
        } else {
            if ($(btnNext).hasClass('installation-final')) {
                $(btnNext).parents('.installation-form').find('.step').removeClass('active');
                $(btnNext).parents('.installation-form').find('.content').removeClass('active');

                $(btnNext).parents('.installation-form').find('.step[data-target="#loader"]').addClass('active');
                $(btnNext).parents('.installation-form').find('#loader').addClass('active');
            }
        }

       $(input).each(function() {
            if ($(this).val() === '') {
                $(this).addClass('is-invalid');
                $(this).prev().addClass('text-danger');
            } else {
                $(this).removeClass('is-invalid');
                $(this).prev().removeClass('text-danger');
            }
        });
    });

    $(document).on('keydown', function (event) {
        if (event.which == 13 && $('.installation-form').length > 0) {
            event.preventDefault();

            $('.installation-content.active').find('.installation-next').click();
        }
    });

});