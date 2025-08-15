//Render loader
function createLoader(options = {}) {
    const {
        text = '',
        spinnerClass = ''
    } = options;

    return `
        <div class="d-flex flex-column align-items-center justify-content-center text-center position-absolute top-0 start-0 p-3 w-100 h-100 bg-body bg-opacity-75 loader">
            <div class="spinner-border ${spinnerClass}" role="status">
                <span class="visually-hidden">Загрузка...</span>
            </div>
            ${text ? `<span class="mt-2">${text}</span>` : ''}
        </div>
    `;
}

//Add loader
function addLoader(loaderWrapper, options = {}) {
    if (loaderWrapper.find('.loader').length < 1) {
        loaderWrapper.append(createLoader(options));
    }
}

//Delete loader
function deleteLoader(loaderWrapper) {
    loaderWrapper.find('.loader').detach();
}