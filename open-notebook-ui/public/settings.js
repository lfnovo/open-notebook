document.addEventListener('DOMContentLoaded', () => {
    fetchSettingsData();
    setupSaveSettingsButton();
});

async function fetchSettingsData() {
    const docEngineSelect = document.getElementById('doc-processing-engine');
    const urlEngineSelect = document.getElementById('url-processing-engine');
    const embeddingOptionSelect = document.getElementById('embedding-option');
    const autoDeleteFilesSelect = document.getElementById('auto-delete-files');
    const firecrawlStatus = document.getElementById('firecrawl-status');
    const jinaStatus = document.getElementById('jina-status');

    try {
        const response = await fetch('/api/settings/content');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        const settings = await response.json();

        // Set current values
        docEngineSelect.value = settings.default_content_processing_engine_doc || 'auto';
        urlEngineSelect.value = settings.default_content_processing_engine_url || 'auto';
        embeddingOptionSelect.value = settings.default_embedding_option || 'ask';
        autoDeleteFilesSelect.value = settings.auto_delete_files || 'yes';

        // Fetch provider status for Firecrawl and Jina
        const providersResponse = await fetch('/api/models/providers'); // Reusing models API for provider status
        if (!providersResponse.ok) throw new Error(`HTTP error! status: ${providersResponse.status}`);
        const providersData = await providersResponse.json();
        const providerStatus = providersData.provider_status;

        if (providerStatus.firecrawl) {
            firecrawlStatus.innerHTML = '<span class="status-indicator online"></span>Configured';
            firecrawlStatus.setAttribute('data-full-message', 'Firecrawl API Key is configured.');
        } else {
            firecrawlStatus.innerHTML = '<span class="status-indicator offline"></span>Not configured';
            firecrawlStatus.setAttribute('data-full-message', 'Firecrawl API Key missing. You need to add FIRECRAWL_API_KEY to use it. Get a key at Firecrawl.dev. If you don\'t add one, it will default to Jina.');
        }

        if (providerStatus.jina) {
            jinaStatus.innerHTML = '<span class="status-indicator online"></span>Configured';
            jinaStatus.setAttribute('data-full-message', 'Jina API Key is configured.');
        } else {
            jinaStatus.innerHTML = '<span class="status-indicator warning"></span>Missing Key';
            jinaStatus.setAttribute('data-full-message', 'Jina API Key missing. It will work for a few requests a day, but fallback to simple afterwards. Please add JINA_API_KEY to prevent that. Get a key at Jina.ai.');
        }

    } catch (error) {
        console.error('Error fetching settings data:', error);
        showError(`Failed to load settings: ${error.message}`);
    }
}

function setupSaveSettingsButton() {
    const saveBtn = document.getElementById('save-settings-btn');
    saveBtn.addEventListener('click', async () => {
        const docEngine = document.getElementById('doc-processing-engine').value;
        const urlEngine = document.getElementById('url-processing-engine').value;
        const embeddingOption = document.getElementById('embedding-option').value;
        const autoDeleteFiles = document.getElementById('auto-delete-files').value;

        const settingsUpdates = {
            default_content_processing_engine_doc: docEngine,
            default_content_processing_engine_url: urlEngine,
            default_embedding_option: embeddingOption,
            auto_delete_files: autoDeleteFiles,
        };

        try {
            const response = await fetch('/api/settings/content', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(settingsUpdates),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }

            showSuccess('Settings saved successfully!');
            fetchSettingsData(); // Refresh to show updated status messages if any
        } catch (error) {
            console.error('Error saving settings:', error);
            showError(`Failed to save settings: ${error.message}`);
        }
    });
}
