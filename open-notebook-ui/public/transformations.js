document.addEventListener('DOMContentLoaded', () => {
    fetchTransformationData();
    setupAddTransformationForm();
    setupEditTransformationModal(); // New function call
});

async function fetchTransformationData() {
    await fetchDefaultPrompt();
    await fetchTransformationsList();
}

async function fetchDefaultPrompt() {
    const container = document.getElementById('default-prompt-container');
    container.innerHTML = `
        <div class="loading-skeleton">
            <div class="skeleton-item">
                <div class="skeleton-line long"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line short"></div>
            </div>
        </div>
    `;
    try {
        const response = await fetch('/api/transformations/defaults');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        container.innerHTML = `
            <textarea id="default-transformation-instructions">${data.transformation_instructions || ''}</textarea>
            <button id="save-default-prompt-btn">Save</button>
        `;

        document.getElementById('save-default-prompt-btn').addEventListener('click', async () => {
            const instructions = document.getElementById('default-transformation-instructions').value.trim();
            await updateDefaultPrompt(instructions);
        });

    } catch (error) {
        console.error('Error fetching default prompt:', error);
        container.innerHTML = `<p style="color: red;">Error loading default prompt: ${error.message}</p>`;
    }
}

async function updateDefaultPrompt(instructions) {
    try {
        const response = await fetch('/api/transformations/defaults', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ transformation_instructions: instructions }),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        showSuccess('Default prompt updated successfully!');
        fetchDefaultPrompt(); // Refresh
    } catch (error) {
        console.error('Error updating default prompt:', error);
        showError(`Failed to update default prompt: ${error.message}`);
    }
}

async function fetchTransformationsList() {
    const container = document.getElementById('transformations-list-container');
    container.innerHTML = `
        <div class="loading-skeleton">
            <div class="skeleton-item">
                <div class="skeleton-title"></div>
                <div class="skeleton-line medium"></div>
                <div class="skeleton-line short"></div>
            </div>
            <div class="skeleton-item">
                <div class="skeleton-title"></div>
                <div class="skeleton-line long"></div>
                <div class="skeleton-line medium"></div>
            </div>
        </div>
    `;
    try {
        const response = await fetch('/api/transformations/all');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const transformations = await response.json();

        if (transformations.length === 0) {
            container.innerHTML = '<p>No transformations created yet. Click "Create Transformation" to get started.</p>';
            return;
        }

        let html = '';
        transformations.forEach(t => {
            html += `
                <div class="transformation-card">
                    <h4>${t.name} ${t.apply_default ? ' - default' : ''}</h4>
                    <p>Title: ${t.title}</p>
                    <p>Description: ${t.description}</p>
                    <p>Prompt: ${t.prompt.substring(0, 100)}...</p>
                    <div class="actions">
                        <button class="edit-transformation-btn" data-id="${t.id}">Edit</button>
                        <button class="delete-transformation-btn delete-btn" data-id="${t.id}">Delete</button>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

        document.querySelectorAll('.edit-transformation-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const transformationId = event.target.dataset.id;
                openEditTransformationModal(transformationId);
            });
        });

        document.querySelectorAll('.delete-transformation-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const transformationId = event.target.dataset.id;
                const confirmed = await showConfirm(`Are you sure you want to delete transformation ${transformationId}?`, 'Confirm Deletion', 'error');
                if (confirmed) {
                    await deleteTransformation(transformationId);
                }
            });
        });

    } catch (error) {
        console.error('Error fetching transformations:', error);
        container.innerHTML = `<p style="color: red;">Error loading transformations: ${error.message}</p>`;
    }
}

function setupAddTransformationForm() {
    const form = document.getElementById('add-transformation-form');
    const nameInput = document.getElementById('add-transformation-name');
    const titleInput = document.getElementById('add-transformation-title');
    const descriptionTextarea = document.getElementById('add-transformation-description');
    const promptTextarea = document.getElementById('add-transformation-prompt');
    const applyDefaultCheckbox = document.getElementById('add-transformation-default');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = nameInput.value.trim();
        const title = titleInput.value.trim();
        const description = descriptionTextarea.value.trim();
        const prompt = promptTextarea.value.trim();
        const apply_default = applyDefaultCheckbox.checked;

        if (!name || !title || !description || !prompt) {
            showError('Please fill all required fields.');
            return;
        }

        try {
            const response = await fetch('/api/transformations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, title, description, prompt, apply_default }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }
            showSuccess('Transformation added successfully!');
            fetchTransformationData(); // Refresh list
            form.reset();
        } catch (error) {
            console.error('Error adding transformation:', error);
            showError(`Failed to add transformation: ${error.message}`);
        }
    });
}

async function deleteTransformation(transformationId) {
    try {
        const response = await fetch(`/api/transformations/${transformationId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        showSuccess('Transformation deleted successfully!');
        fetchTransformationData(); // Refresh list
    } catch (error) {
        console.error('Error deleting transformation:', error);
        showError(`Failed to delete transformation: ${error.message}`);
    }
}

// Edit Transformation Modal Logic
function setupEditTransformationModal() {
    const mainContent = document.getElementById('main-content'); // Assuming main-content is the parent
    const modalHtml = `
        <div id="edit-transformation-modal" class="modal">
            <div class="modal-content">
                <span class="close-button">&times;</span>
                <h2>Edit Transformation</h2>
                <form id="edit-transformation-form">
                    <input type="hidden" id="edit-transformation-id">
                    <label for="edit-transformation-name">Name:</label>
                    <input type="text" id="edit-transformation-name-input" required>

                    <label for="edit-transformation-title">Card Title:</label>
                    <input type="text" id="edit-transformation-title-input" required>

                    <label for="edit-transformation-description">Description:</label>
                    <textarea id="edit-transformation-description-input"></textarea>

                    <label for="edit-transformation-prompt">Prompt:</label>
                    <textarea id="edit-transformation-prompt-input" required></textarea>

                    <label>
                        <input type="checkbox" id="edit-transformation-default-checkbox"> Suggest by default on new sources
                    </label>

                    <button type="submit">Save Changes</button>
                    <button type="button" id="cancel-edit-transformation-btn">Cancel</button>
                </form>
            </div>
        </div>
    `;
    mainContent.insertAdjacentHTML('beforeend', modalHtml);

    const editTransformationModal = document.getElementById('edit-transformation-modal');
    const closeButton = editTransformationModal.querySelector('.close-button');
    const cancelEditBtn = document.getElementById('cancel-edit-transformation-btn');
    const editTransformationForm = document.getElementById('edit-transformation-form');

    closeButton.addEventListener('click', () => {
        editTransformationModal.style.display = 'none';
    });

    cancelEditBtn.addEventListener('click', () => {
        editTransformationModal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target == editTransformationModal) {
            editTransformationModal.style.display = 'none';
        }
    });

    editTransformationForm.addEventListener('submit', async (event) => {
        event.preventDefault();
        const id = document.getElementById('edit-transformation-id').value;
        const name = document.getElementById('edit-transformation-name-input').value.trim();
        const title = document.getElementById('edit-transformation-title-input').value.trim();
        const description = document.getElementById('edit-transformation-description-input').value.trim();
        const prompt = document.getElementById('edit-transformation-prompt-input').value.trim();
        const apply_default = document.getElementById('edit-transformation-default-checkbox').checked;

        if (!name || !title || !description || !prompt) {
            showError('Please fill all required fields.');
            return;
        }

        try {
            const response = await fetch(`/api/transformations/${id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, title, description, prompt, apply_default }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }
            showSuccess('Transformation updated successfully!');
            editTransformationModal.style.display = 'none';
            fetchTransformationData(); // Refresh list
        } catch (error) {
            console.error('Error updating transformation:', error);
            showError(`Failed to update transformation: ${error.message}`);
        }
    });
}

async function openEditTransformationModal(transformationId) {
    const editTransformationModal = document.getElementById('edit-transformation-modal');
    const idInput = document.getElementById('edit-transformation-id');
    const nameInput = document.getElementById('edit-transformation-name-input');
    const titleInput = document.getElementById('edit-transformation-title-input');
    const descriptionTextarea = document.getElementById('edit-transformation-description-input');
    const promptTextarea = document.getElementById('edit-transformation-prompt-input');
    const applyDefaultCheckbox = document.getElementById('edit-transformation-default-checkbox');

    try {
        const response = await fetch(`/api/transformations/${transformationId}`);
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const transformation = await response.json();

        idInput.value = transformation.id;
        nameInput.value = transformation.name;
        titleInput.value = transformation.title;
        descriptionTextarea.value = transformation.description || '';
        promptTextarea.value = transformation.prompt;
        applyDefaultCheckbox.checked = transformation.apply_default;

        editTransformationModal.style.display = 'block';
    } catch (error) {
        console.error('Error fetching transformation details for edit:', error);
        showError(`Failed to load transformation details: ${error.message}`);
    }
}
