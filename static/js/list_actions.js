class ListActionButton extends HTMLButtonElement {
    connectedCallback() {
        this.addEventListener('click', this.handleClick)
    }

    disconnectedCallback() {
        this.removeEventListener('click', this.handleClick)
    }

    handleClick = e => {
        if (this.form) {
            this.form[this.name][0].value = this.value;
            for (const action of this.form[this.dataset.checkboxName]) {
                if (action.value === this.dataset.checkboxValue) {
                    action.checked = true;
                }
            }
            this.form.submit()
        }
    }
}

customElements.define('list-action-button', ListActionButton, {extends: 'button'});