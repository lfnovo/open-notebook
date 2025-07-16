document.addEventListener('DOMContentLoaded', () => {
    fetchModelData();
    setupAddModelForm();
});

async function fetchModelData() {
    await fetchProviderStatus();
    await fetchConfiguredModels();
    await fetchDefaultModels();
}

async function fetchProviderStatus() {
    const container = document.getElementById('provider-status-container');
    container.innerHTML = 'Loading provider status...';
    try {
        const response = await fetch('/api/models/providers');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const data = await response.json();

        let html = '<div class="provider-grid">';
        for (const provider in data.provider_status) {
            const status = data.provider_status[provider];
            html += `
                <div class="provider-card ${status ? 'available' : 'unavailable'}">
                    <div class="provider-header">
                        <span class="provider-name">${provider}</span>
                        <span class="provider-status ${status ? 'available' : 'unavailable'}">${status ? 'Available' : 'Unavailable'}</span>
                    </div>
                </div>
            `;
        }
        html += '</div>';
        container.innerHTML = html;

        // Populate provider dropdown for adding new models
        const addModelProviderSelect = document.getElementById('add-model-provider');
        addModelProviderSelect.innerHTML = '<option value="">Select Provider</option>';
        const modelTypeSelect = document.getElementById('add-model-type');

        const updateProviders = () => {
            const selectedType = modelTypeSelect.value;
            addModelProviderSelect.innerHTML = '<option value="">Select Provider</option>';
            if (selectedType && data.available_providers[selectedType]) {
                const providersForType = data.available_providers[selectedType].sort();
                providersForType.forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider;
                    option.textContent = provider;
                    addModelProviderSelect.appendChild(option);
                });
            }
        };
        modelTypeSelect.addEventListener('change', updateProviders);
        updateProviders(); // Initial population
    } catch (error) {
        console.error('Error fetching provider status:', error);
        container.innerHTML = `<p style="color: red;">Error loading provider status: ${error.message}</p>`;
    }
}

async function fetchConfiguredModels() {
    const container = document.getElementById('configured-models-container');
    container.innerHTML = 'Loading configured models...';
    try {
        const response = await fetch('/api/models/all');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const models = await response.json();

        if (models.length === 0) {
            container.innerHTML = '<p>No models configured yet.</p>';
            return;
        }

        let html = '';
        models.sort((a, b) => {
            if (a.type === b.type) {
                return a.provider.localeCompare(b.provider) || a.name.localeCompare(b.name);
            }
            return a.type.localeCompare(b.type);
        });

        models.forEach(model => {
            html += `
                <div class="model-card">
                    <span>${model.type}: ${model.provider} - ${model.name}</span>
                    <button data-id="${model.id}" class="delete-model-btn">Delete</button>
                </div>
            `;
        });
        container.innerHTML = html;

        document.querySelectorAll('.delete-model-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const modelId = event.target.dataset.id;
                if (confirm(`Are you sure you want to delete model ${modelId}?`)) {
                    await deleteModel(modelId);
                }
            });
        });

    } catch (error) {
        console.error('Error fetching configured models:', error);
        container.innerHTML = `<p style="color: red;">Error loading configured models: ${error.message}</p>`;
    }
}

async function fetchDefaultModels() {
    const container = document.getElementById('default-models-container');
    container.innerHTML = 'Loading default models...';
    try {
        const response = await fetch('/api/models/defaults');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const defaultModels = await response.json();

        const modelTypes = [
            { key: 'default_chat_model', label: 'Chat Model', type: 'language', help: 'Used for chat conversations' },
            { key: 'default_tools_model', label: 'Tools Model', type: 'language', help: 'Used for calling tools - use OpenAI or Anthropic' },
            { key: 'default_transformation_model', label: 'Transformation Model', type: 'language', help: 'Used for summaries, insights, etc.' },
            { key: 'large_context_model', label: 'Large Context Model', type: 'language', help: 'Used for large context processing' },
            { key: 'default_embedding_model', label: 'Embedding Model', type: 'embedding', help: 'Used for semantic search and embeddings' },
            { key: 'default_text_to_speech_model', label: 'Default TTS Model', type: 'text_to_speech', help: 'Used for podcasts and audio generation' },
            { key: 'default_speech_to_text_model', label: 'Default STT Model', type: 'speech_to_text', help: 'Used for audio transcriptions' },
        ];

        let html = '';
        for (const modelTypeConfig of modelTypes) {
            const modelsOfTypeResponse = await fetch(`/api/models/by_type/${modelTypeConfig.type}`);
            const modelsOfType = await modelsOfTypeResponse.json();

            let optionsHtml = '<option value="">None</option>';
            modelsOfType.forEach(model => {
                const selected = defaultModels[modelTypeConfig.key] === model.id ? 'selected' : '';
                optionsHtml += `<option value="${model.id}" ${selected}>${model.provider} - ${model.name}</option>`;
            });

            html += `
                <div class="default-model-assignment">
                    <label for="${modelTypeConfig.key}">${modelTypeConfig.label}:</label>
                    <select id="${modelTypeConfig.key}" data-model-key="${modelTypeConfig.key}" title="${modelTypeConfig.help}">
                        ${optionsHtml}
                    </select>
                    <p class="help-text">${modelTypeConfig.help}</p>
                </div>
            `;
        }
        container.innerHTML = html;

        document.querySelectorAll('.default-model-assignment select').forEach(selectElement => {
            selectElement.addEventListener('change', async (event) => {
                const modelKey = event.target.dataset.modelKey;
                const selectedModelId = event.target.value;
                await updateDefaultModel(modelKey, selectedModelId);
            });
        });

    } catch (error) {
        console.error('Error fetching default models:', error);
        container.innerHTML = `<p style="color: red;">Error loading default models: ${error.message}</p>`;
    }
}

function setupAddModelForm() {
    const form = document.getElementById('add-model-form');
    const nameInput = document.getElementById('add-model-name');
    const providerSelect = document.getElementById('add-model-provider');
    const typeSelect = document.getElementById('add-model-type');

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const name = nameInput.value.trim();
        const provider = providerSelect.value;
        const type = typeSelect.value;

        if (!name || !provider || !type) {
            alert('Please fill all fields.');
            return;
        }

        try {
            const response = await fetch('/api/models', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, provider, type }),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }
            alert('Model added successfully!');
            fetchModelData(); // Refresh all model data
            form.reset();
        } catch (error) {
            console.error('Error adding model:', error);
            alert(`Failed to add model: ${error.message}`);
        }
    });
}

async function deleteModel(modelId) {
    try {
        const response = await fetch(`/api/models/${modelId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        alert('Model deleted successfully!');
        fetchModelData(); // Refresh all model data
    } catch (error) {
        console.error('Error deleting model:', error);
        alert(`Failed to delete model: ${error.message}`);
    }
}

async function updateDefaultModel(modelKey, selectedModelId) {
    try {
        const payload = {};
        payload[modelKey] = selectedModelId;

        const response = await fetch('/api/models/defaults', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        alert('Default model updated successfully!');
        fetchModelData(); // Refresh all model data
    } catch (error) {
        console.error('Error updating default model:', error);
        alert(`Failed to update default model: ${error.message}`);
    }
}
