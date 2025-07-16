document.addEventListener('DOMContentLoaded', () => {
    fetchPodcastData();
    setupAddPodcastTemplateForm();
});

async function fetchPodcastData() {
    await fetchPodcastEpisodes();
    await fetchPodcastTemplates();
}

async function fetchPodcastEpisodes() {
    const container = document.getElementById('episodes-list-container');
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
        const response = await fetch('/api/podcasts/episodes');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const episodes = await response.json();

        if (episodes.length === 0) {
            container.innerHTML = '<p>No podcast episodes generated yet. Create a podcast template and generate episodes from your notebooks.</p>';
            return;
        }

        let html = '';
        episodes.forEach(episode => {
            html += `
                <div class="podcast-episode-card">
                    <h4>${episode.title || 'Untitled Episode'}</h4>
                    <p>Notebook: ${episode.notebook_name || 'Unknown'}</p>
                    <p>Template: ${episode.template_name || 'Unknown'}</p>
                    <p>Generated: ${new Date(episode.created).toLocaleString()}</p>
                    <div class="episode-actions">
                        <button class="play-episode-btn" data-id="${episode.id}">▶ Play</button>
                        <button class="download-episode-btn" data-id="${episode.id}">⬇ Download</button>
                        <button class="delete-episode-btn delete-btn" data-id="${episode.id}">Delete</button>
                    </div>
                    ${episode.audio_url ? `<audio controls><source src="${episode.audio_url}" type="audio/mpeg"></audio>` : ''}
                </div>
            `;
        });
        container.innerHTML = html;

        // Add event listeners
        document.querySelectorAll('.delete-episode-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const episodeId = event.target.dataset.id;
                if (confirm(`Are you sure you want to delete this episode ${episodeId}?`)) {
                    await deletePodcastEpisode(episodeId);
                }
            });
        });

    } catch (error) {
        console.error('Error fetching podcast episodes:', error);
        container.innerHTML = `<p style="color: red;">Error loading podcast episodes: ${error.message}</p>`;
    }
}

async function deletePodcastEpisode(episodeId) {
    try {
        const response = await fetch(`/api/podcasts/episodes/${episodeId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        alert('Episode deleted successfully!');
        fetchPodcastEpisodes(); // Refresh list
    } catch (error) {
        console.error('Error deleting episode:', error);
        alert(`Failed to delete episode: ${error.message}`);
    }
}

async function fetchPodcastTemplates() {
    const container = document.getElementById('templates-list-container');
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
        const response = await fetch('/api/podcasts/configs');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const templates = await response.json();

        if (templates.length === 0) {
            container.innerHTML = '<p>No podcast templates created yet. Create your first template below.</p>';
            return;
        }

        let html = '';
        templates.forEach(template => {
            html += `
                <div class="podcast-template-card">
                    <h4>${template.name}</h4>
                    <p>Provider: ${template.provider}</p>
                    <p>Type: ${template.type}</p>
                    <p>Created: ${new Date(template.created).toLocaleString()}</p>
                    <div class="template-actions">
                        <button class="generate-episode-btn" data-id="${template.id}">🎙️ Generate Episode</button>
                        <button class="edit-template-btn" data-id="${template.id}">Edit</button>
                        <button class="delete-template-btn delete-btn" data-id="${template.id}">Delete</button>
                    </div>
                </div>
            `;
        });
        container.innerHTML = html;

        // Add event listeners
        document.querySelectorAll('.generate-episode-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const templateId = event.target.dataset.id;
                alert('Episode generation feature would be implemented here');
            });
        });

        document.querySelectorAll('.edit-template-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const templateId = event.target.dataset.id;
                // Implement edit modal/form later
                alert(`Edit template: ${templateId}`);
            });
        });

        document.querySelectorAll('.delete-template-btn').forEach(button => {
            button.addEventListener('click', async (event) => {
                const templateId = event.target.dataset.id;
                if (confirm(`Are you sure you want to delete this podcast template ${templateId}?`)) {
                    await deletePodcastTemplate(templateId);
                }
            });
        });

    } catch (error) {
        console.error('Error fetching podcast templates:', error);
        container.innerHTML = `<p style="color: red;">Error loading podcast templates: ${error.message}</p>`;
    }
}

async function deletePodcastTemplate(templateId) {
    try {
        const response = await fetch(`/api/podcasts/configs/${templateId}`, {
            method: 'DELETE',
        });
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }
        alert('Podcast template deleted successfully!');
        fetchPodcastTemplates(); // Refresh list
    } catch (error) {
        console.error('Error deleting podcast template:', error);
        alert(`Failed to delete podcast template: ${error.message}`);
    }
}

function setupAddPodcastTemplateForm() {
    const form = document.getElementById('add-template-form');
    const transcriptModelProviderSelect = document.getElementById('transcript-model-provider');
    const transcriptModelSelect = document.getElementById('transcript-model');
    const audioModelProviderSelect = document.getElementById('audio-model-provider');
    const audioModelSelect = document.getElementById('audio-model');

    // Fetch available models to populate dropdowns
    fetch('/api/models/providers').then(res => res.json()).then(data => {
        const availableProviders = data.available_providers;

        const populateModelSelect = (selectElement, modelType, selectedProvider) => {
            selectElement.innerHTML = '<option value="">Select Model</option>';
            if (selectedProvider && availableProviders[modelType]) {
                const modelsForProvider = availableProviders[modelType].filter(model => model.startsWith(selectedProvider)); // Simple filter for now
                modelsForProvider.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    selectElement.appendChild(option);
                });
            }
        };

        // Populate provider dropdowns
        const populateProviderSelect = (selectElement, modelType) => {
            selectElement.innerHTML = '<option value="">Select Provider</option>';
            if (availableProviders[modelType]) {
                const providers = [...new Set(availableProviders[modelType].map(model => model.split(':')[0]))].sort(); // Extract unique providers
                providers.forEach(provider => {
                    const option = document.createElement('option');
                    option.value = provider;
                    option.textContent = provider;
                    selectElement.appendChild(option);
                });
            }
        };

        populateProviderSelect(transcriptModelProviderSelect, 'language');
        populateProviderSelect(audioModelProviderSelect, 'text_to_speech');

        transcriptModelProviderSelect.addEventListener('change', () => {
            populateModelSelect(transcriptModelSelect, 'language', transcriptModelProviderSelect.value);
        });
        audioModelProviderSelect.addEventListener('change', () => {
            populateModelSelect(audioModelSelect, 'text_to_speech', audioModelProviderSelect.value);
        });
    });

    form.addEventListener('submit', async (event) => {
        event.preventDefault();
        const configData = {
            name: document.getElementById('template-name').value.trim(),
            podcast_name: document.getElementById('podcast-name').value.trim(),
            podcast_tagline: document.getElementById('podcast-tagline').value.trim(),
            output_language: document.getElementById('output-language').value.trim(),
            user_instructions: document.getElementById('user-instructions').value.trim(),
            person1_role: document.getElementById('person1-role').value.split(',').map(s => s.trim()).filter(s => s),
            person2_role: document.getElementById('person2-role').value.split(',').map(s => s.trim()).filter(s => s),
            conversation_style: document.getElementById('conversation-style').value.split(',').map(s => s.trim()).filter(s => s),
            engagement_technique: document.getElementById('engagement-technique').value.split(',').map(s => s.trim()).filter(s => s),
            dialogue_structure: document.getElementById('dialogue-structure').value.split(',').map(s => s.trim()).filter(s => s),
            creativity: parseFloat(document.getElementById('creativity').value),
            ending_message: document.getElementById('ending-message').value.trim(),
            transcript_model_provider: transcriptModelProviderSelect.value,
            transcript_model: transcriptModelSelect.value,
            provider: audioModelProviderSelect.value,
            model: audioModelSelect.value,
            voice1: document.getElementById('voice1').value.trim(),
            voice2: document.getElementById('voice2').value.trim(),
        };

        // Basic validation
        for (const key of ['name', 'podcast_name', 'podcast_tagline', 'output_language', 'transcript_model_provider', 'transcript_model', 'provider', 'model', 'voice1', 'voice2']) {
            if (!configData[key] || (Array.isArray(configData[key]) && configData[key].length === 0)) {
                alert(`Please fill in the ${key.replace(/_/g, ' ')} field.`);
                return;
            }
        }

        try {
            const response = await fetch('/api/podcasts/configs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(configData),
            });
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }
            alert('Podcast template added successfully!');
            fetchPodcastTemplates(); // Refresh list
            form.reset();
        } catch (error) {
            console.error('Error adding podcast template:', error);
            alert(`Failed to add podcast template: ${error.message}`);
        }
    });
}
