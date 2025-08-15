//Create message
function createMessage(messageText, messageWrapper, messageType) {
    let message = $('<div class="toast align-items-center ' + messageType + ' border-0" role="alert" aria-live="assertive" aria-atomic="true">' +
                        '<div class="d-flex">' +
                            '<div class="toast-body">' +
                                messageText +
                            '</div>' +
                            '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
                        '</div>' +
                    '</div>');
    messageWrapper.append(message);

    const messageToast = $('.toast');
    const toastBootstrap = bootstrap.Toast.getOrCreateInstance(messageToast);

    $(messageToast).fadeIn(function() {
        messageToast.addClass('show');
    });

    setTimeout(() => {
        $(messageToast).fadeOut(function() {
            toastBootstrap.hide();
        });
    }, '1500');

    messageToast.on('hidden.bs.toast', () => {
        deleteMessage(messageToast);
    });
};

//Delete message
function deleteMessage(message) {
    message.detach();
};