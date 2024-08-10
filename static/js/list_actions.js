class ListActionsDropdown extends HTMLElement {
    connectedCallback() {
        this.addEventListener('click', this.handleClick)
    }

    disconnectedCallback() {
        this.removeEventListener('click', this.handleClick)
    }

    handleClick = (e) => {
        const form = this.closest('form')
        const item = e.target.closest('.list-action-item')
        if (form && item) {
            form[this.dataset.dropdownName][0].value = item.dataset.action;
            if (form[this.dataset.checkboxName] instanceof HTMLElement) {
                if (form[this.dataset.checkboxName].value === this.dataset.checkboxValue) {
                    form[this.dataset.checkboxName].checked = true;
                }
            } else {
                for (const action of form[this.dataset.checkboxName]) {
                    if (action.value === this.dataset.checkboxValue) {
                        action.checked = true;
                    }
                }
            }

            form.submit()
        }
    }
}

customElements.define('list-actions-dropdown', ListActionsDropdown);