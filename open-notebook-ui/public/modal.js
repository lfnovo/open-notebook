/**
 * Custom Modal System - Replaces browser alerts with styled modals
 */

class CustomModal {
    constructor() {
        this.modalContainer = null;
        this.currentModal = null;
        this.init();
    }

    init() {
        // Create modal container if it doesn't exist
        if (!document.getElementById('custom-modal-container')) {
            this.modalContainer = document.createElement('div');
            this.modalContainer.id = 'custom-modal-container';
            this.modalContainer.className = 'custom-modal-overlay';
            document.body.appendChild(this.modalContainer);
        } else {
            this.modalContainer = document.getElementById('custom-modal-container');
        }
    }

    /**
     * Show an alert modal (replaces window.alert)
     * @param {string} message - The message to display
     * @param {string} title - Optional title (default: "Alert")
     * @param {string} type - Type of alert: 'info', 'success', 'warning', 'error' (default: 'info')
     * @returns {Promise} - Resolves when modal is closed
     */
    alert(message, title = 'Alert', type = 'info') {
        return new Promise((resolve) => {
            this.show({
                title,
                message,
                type,
                buttons: [
                    {
                        text: 'OK',
                        class: 'btn-primary',
                        action: () => {
                            this.hide();
                            resolve();
                        }
                    }
                ]
            });
        });
    }

    /**
     * Show a confirmation modal (replaces window.confirm)
     * @param {string} message - The message to display
     * @param {string} title - Optional title (default: "Confirm")
     * @param {string} type - Type of confirmation: 'info', 'warning', 'error' (default: 'warning')
     * @returns {Promise<boolean>} - Resolves with true/false based on user choice
     */
    confirm(message, title = 'Confirm', type = 'warning') {
        return new Promise((resolve) => {
            this.show({
                title,
                message,
                type,
                buttons: [
                    {
                        text: 'Cancel',
                        class: 'btn-secondary',
                        action: () => {
                            this.hide();
                            resolve(false);
                        }
                    },
                    {
                        text: 'OK',
                        class: type === 'error' ? 'btn-danger' : 'btn-primary',
                        action: () => {
                            this.hide();
                            resolve(true);
                        }
                    }
                ]
            });
        });
    }

    /**
     * Show a custom modal
     * @param {Object} options - Modal configuration
     * @param {string} options.title - Modal title
     * @param {string} options.message - Modal message
     * @param {string} options.type - Modal type: 'info', 'success', 'warning', 'error'
     * @param {Array} options.buttons - Array of button objects
     * @param {boolean} options.closable - Whether modal can be closed by clicking overlay (default: true)
     */
    show(options) {
        const {
            title = 'Modal',
            message = '',
            type = 'info',
            buttons = [],
            closable = true
        } = options;

        // Hide any existing modal
        this.hide();

        // Create modal HTML
        const modalHTML = `
            <div class="custom-modal-content ${type}">
                <div class="custom-modal-header">
                    <div class="custom-modal-icon ${type}">
                        ${this.getIcon(type)}
                    </div>
                    <h3 class="custom-modal-title">${title}</h3>
                    ${closable ? '<button class="custom-modal-close" aria-label="Close">&times;</button>' : ''}
                </div>
                <div class="custom-modal-body">
                    <p class="custom-modal-message">${message}</p>
                </div>
                <div class="custom-modal-footer">
                    ${buttons.map(button => `
                        <button class="btn ${button.class || 'btn-secondary'}" data-action="${buttons.indexOf(button)}">
                            ${button.text || 'OK'}
                        </button>
                    `).join('')}
                </div>
            </div>
        `;

        this.modalContainer.innerHTML = modalHTML;
        this.modalContainer.style.display = 'flex';
        this.currentModal = this.modalContainer.querySelector('.custom-modal-content');

        // Add event listeners
        if (closable) {
            const closeBtn = this.modalContainer.querySelector('.custom-modal-close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.hide());
            }

            this.modalContainer.addEventListener('click', (e) => {
                if (e.target === this.modalContainer) {
                    this.hide();
                }
            });
        }

        // Add button event listeners
        buttons.forEach((button, index) => {
            const btnElement = this.modalContainer.querySelector(`[data-action="${index}"]`);
            if (btnElement && button.action) {
                btnElement.addEventListener('click', button.action);
            }
        });

        // Add keyboard support
        document.addEventListener('keydown', this.handleKeydown.bind(this));

        // Focus first button
        const firstButton = this.modalContainer.querySelector('.btn');
        if (firstButton) {
            setTimeout(() => firstButton.focus(), 100);
        }

        // Animate in
        setTimeout(() => {
            this.currentModal.classList.add('show');
        }, 10);
    }

    /**
     * Hide the current modal
     */
    hide() {
        if (this.currentModal) {
            this.currentModal.classList.remove('show');
            setTimeout(() => {
                this.modalContainer.style.display = 'none';
                this.modalContainer.innerHTML = '';
                this.currentModal = null;
            }, 200);
        }
        document.removeEventListener('keydown', this.handleKeydown.bind(this));
    }

    /**
     * Handle keyboard events
     */
    handleKeydown(e) {
        if (e.key === 'Escape' && this.currentModal) {
            const closeBtn = this.modalContainer.querySelector('.custom-modal-close');
            if (closeBtn) {
                this.hide();
            }
        }
    }

    /**
     * Get icon for modal type
     */
    getIcon(type) {
        const icons = {
            info: '&#8505;',
            success: '&#10004;',
            warning: '&#9888;',
            error: '&#10006;'
        };
        return icons[type] || icons.info;
    }
}

// Create global instance
window.customModal = new CustomModal();

// Override window.alert and window.confirm
window.originalAlert = window.alert;
window.originalConfirm = window.confirm;

window.alert = function(message) {
    return window.customModal.alert(message);
};

window.confirm = function(message) {
    return window.customModal.confirm(message);
};

// Convenience functions for different alert types
window.showSuccess = function(message, title = 'Success') {
    return window.customModal.alert(message, title, 'success');
};

window.showWarning = function(message, title = 'Warning') {
    return window.customModal.alert(message, title, 'warning');
};

window.showError = function(message, title = 'Error') {
    return window.customModal.alert(message, title, 'error');
};

window.showInfo = function(message, title = 'Information') {
    return window.customModal.alert(message, title, 'info');
};

window.showConfirm = function(message, title = 'Confirm', type = 'warning') {
    return window.customModal.confirm(message, title, type);
};
