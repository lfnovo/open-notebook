console.log("Frontend script loaded.");

document.addEventListener('DOMContentLoaded', () => {
    fetchNotebooks();
    setupNewNotebookForm();
    setupSearchFunctionality(); // New function call
});

async function fetchNotebooks() {
    const notebooksContainer = document.getElementById('notebooks-container');
    notebooksContainer.innerHTML = `
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
        const response = await fetch('/api/notebooks');
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const notebooks = await response.json();

        if (notebooks.length === 0) {
            notebooksContainer.innerHTML = '<p>No notebooks found. Create one!</p>';
            return;
        }

        notebooksContainer.innerHTML = ''; // Clear loading message

        notebooks.forEach(notebook => {
            const notebookElement = document.createElement('div');
            notebookElement.className = 'notebook-card'; // Add a class for styling
            notebookElement.innerHTML = `
                <h3>${notebook.name}</h3>
                <p>${notebook.description || 'No description.'}</p>
                <p>Created: ${new Date(notebook.created).toLocaleString()}</p>
                <p>Updated: ${new Date(notebook.updated).toLocaleString()}</p>
                <button class="open-notebook-btn" data-id="${notebook.id}">Open</button>
            `;
            notebooksContainer.appendChild(notebookElement);
        });

        // Add event listeners to the dynamically created buttons
        document.querySelectorAll('.open-notebook-btn').forEach(button => {
            button.addEventListener('click', (event) => {
                const notebookId = event.target.dataset.id;
                displayNotebookDetails(notebookId);
            });
        });

    } catch (error) {
        console.error('Error fetching notebooks:', error);
        notebooksContainer.innerHTML = `<p style="color: red;">Error loading notebooks: ${error.message}</p>`;
    }
}

function setupNewNotebookForm() {
    const form = document.getElementById('new-notebook-form');
    const titleInput = document.getElementById('new-notebook-title');
    const descriptionTextarea = document.getElementById('new-notebook-description');

    form.addEventListener('submit', async (event) => {
        event.preventDefault(); // Prevent default form submission

        const name = titleInput.value.trim();
        const description = descriptionTextarea.value.trim();

        if (!name) {
            showError('Notebook name cannot be empty.');
            return;
        }

        try {
            const response = await fetch('/api/notebooks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                    body: JSON.stringify({ name, description }),
                });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
            }

            const newNotebook = await response.json();
            console.log('Notebook created:', newNotebook);
            showSuccess('Notebook created successfully!');

            // Clear form fields
            titleInput.value = '';
            descriptionTextarea.value = '';

            // Refresh the list of notebooks
            fetchNotebooks();

        } catch (error) {
            console.error('Error creating notebook:', error);
            showError(`Failed to create notebook: ${error.message}`);
        }
    });
}

async function displayNotebookDetails(notebookId) {
    const mainContent = document.querySelector('body'); // Or a more specific container
    mainContent.innerHTML = `
        <div class="loading-skeleton">
            <div class="skeleton-item">
                <div class="skeleton-title"></div>
                <div class="skeleton-line long"></div>
                <div class="skeleton-line medium"></div>
            </div>
            <div class="skeleton-item">
                <div class="skeleton-title"></div>
                <div class="skeleton-line short"></div>
                <div class="skeleton-line medium"></div>
            </div>
        </div>
    `;

    try {
        const response = await fetch(`/api/notebooks/${notebookId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const notebook = await response.json();

        let sourcesHtml = '<h3>Sources</h3>';
        if (notebook.sources && notebook.sources.length > 0) {
            notebook.sources.forEach(source => {
                sourcesHtml += `
                    <div class="source-card">
                        <h4>${source.title || 'No Title'}</h4>
                        <p>${source.full_text ? source.full_text.substring(0, 200) + '...' : 'No content preview.'}</p>
                        <p>Updated: ${new Date(source.updated).toLocaleString()}</p>
                    </div>
                `;
            });
        } else {
            sourcesHtml += '<p>No sources found for this notebook.</p>';
        }

        let notesHtml = '<h3>Notes</h3>';
        if (notebook.notes && notebook.notes.length > 0) {
            notebook.notes.forEach(note => {
                notesHtml += `
                    <div class="note-card">
                        <h4>${note.title || 'No Title'}</h4>
                        <p>${note.content ? note.content.substring(0, 200) + '...' : 'No content preview.'}</p>
                        <p>Updated: ${new Date(note.updated).toLocaleString()}</p>
                    </div>
                `;
            });
        } else {
            notesHtml += '<p>No notes found for this notebook.</p>';
        }


        mainContent.innerHTML = `
            <div class="notebook-detail-header">
                <h1>${notebook.name}</h1>
                <div>
                    <button id="edit-notebook-btn" data-id="${notebook.id}">Edit</button>
                    <button id="archive-notebook-btn" data-id="${notebook.id}" data-archived="${notebook.archived}">${notebook.archived ? 'Unarchive' : 'Archive'}</button>
                    <button id="delete-notebook-btn" data-id="${notebook.id}" class="delete-btn">Delete Forever</button>
                    <button onclick="window.location.reload()">Back to Notebooks</button>
                </div>
            </div>
            <p id="notebook-description-display">${notebook.description || 'No description.'}</p>
            <p>Created: ${new Date(notebook.created).toLocaleString()}</p>
            <p>Updated: ${new Date(notebook.updated).toLocaleString()}</p>

            <div id="edit-notebook-form-container" style="display:none;">
                <h3>Edit Notebook</h3>
                <input type="text" id="edit-notebook-title" value="${notebook.name}" required>
                <textarea id="edit-notebook-description">${notebook.description || ''}</textarea>
                <button id="save-notebook-edit-btn" data-id="${notebook.id}">Save Changes</button>
                <button id="cancel-notebook-edit-btn">Cancel</button>
            </div>

            <div class="notebook-content-sections">
                <div class="sources-section">
                    <div class="section-header">
                        <h3>Sources</h3>
                        <button id="add-source-btn" data-notebook-id="${notebook.id}">➕ Add Source</button>
                    </div>
                    ${sourcesHtml}
                </div>
                <div class="notes-section">
                    <div class="section-header">
                        <h3>Notes</h3>
                        <button id="add-note-btn" data-notebook-id="${notebook.id}">📝 Write a Note</button>
                    </div>
                    ${notesHtml}
                </div>
            </div>

            <div id="add-source-modal" class="modal">
                <div class="modal-content">
                    <span class="close-button">&times;</span>
                    <h2>Add a Source</h2>
                    <form id="add-source-form">
                        <label for="source-type">Type:</label>
                        <select id="source-type">
                            <option value="link">Link</option>
                            <option value="upload">Upload</option>
                            <option value="text">Text</option>
                        </select>

                        <div id="source-link-field" class="source-field">
                            <label for="source-link">Link:</label>
                            <input type="url" id="source-link" placeholder="Enter URL">
                        </div>

                        <div id="source-upload-field" class="source-field" style="display:none;">
                            <label for="source-file">Upload File:</label>
                            <input type="file" id="source-file">
                        </div>

                        <div id="source-text-field" class="source-field" style="display:none;">
                            <label for="source-text">Text Content:</label>
                            <textarea id="source-text" placeholder="Enter text content"></textarea>
                        </div>

                        <button type="submit">Process Source</button>
                    </form>
                </div>
            </div>

            <div id="add-note-modal" class="modal">
                <div class="modal-content">
                    <span class="close-button">&times;</span>
                    <h2>Write a Note</h2>
                    <form id="add-note-form">
                        <label for="note-title">Title:</label>
                        <input type="text" id="note-title" placeholder="Enter note title">

                        <label for="note-content">Content:</label>
                        <textarea id="note-content" placeholder="Enter note content"></textarea>

                        <button type="submit">Save Note</button>
                    </form>
                </div>
            </div>
        `;

        // Setup event listeners for detail page buttons
        document.getElementById('edit-notebook-btn').addEventListener('click', () => {
            document.getElementById('notebook-description-display').style.display = 'none';
            document.getElementById('edit-notebook-form-container').style.display = 'block';
        });

        document.getElementById('cancel-notebook-edit-btn').addEventListener('click', () => {
            document.getElementById('notebook-description-display').style.display = 'block';
            document.getElementById('edit-notebook-form-container').style.display = 'none';
        });

        document.getElementById('save-notebook-edit-btn').addEventListener('click', async (event) => {
            const updatedName = document.getElementById('edit-notebook-title').value.trim();
            const updatedDescription = document.getElementById('edit-notebook-description').value.trim();
            await updateNotebook(notebookId, updatedName, updatedDescription, notebook.archived);
        });

        document.getElementById('archive-notebook-btn').addEventListener('click', async (event) => {
            const isArchived = event.target.dataset.archived === 'true';
            await updateNotebook(notebookId, notebook.name, notebook.description, !isArchived);
        });

        document.getElementById('delete-notebook-btn').addEventListener('click', async () => {
            const confirmed = await showConfirm('Are you sure you want to delete this notebook forever? This action cannot be undone.', 'Confirm Deletion', 'error');
            if (confirmed) {
                await deleteNotebook(notebookId);
            }
        });

        // Add Source Modal Logic
        const addSourceBtn = document.getElementById('add-source-btn');
        const addSourceModal = document.getElementById('add-source-modal');
        const closeSourceModalButton = addSourceModal.querySelector('.close-button');
        const sourceTypeSelect = document.getElementById('source-type');
        const sourceLinkField = document.getElementById('source-link-field');
        const sourceUploadField = document.getElementById('source-upload-field');
        const sourceTextField = document.getElementById('source-text-field');
        const addSourceForm = document.getElementById('add-source-form'); // Get the form

        addSourceBtn.addEventListener('click', () => {
            addSourceModal.style.display = 'block';
            // Set the notebook ID on the form for submission
            addSourceForm.dataset.notebookId = notebookId;
        });

        closeSourceModalButton.addEventListener('click', () => {
            addSourceModal.style.display = 'none';
        });

        window.addEventListener('click', (event) => {
            if (event.target == addSourceModal) {
                addSourceModal.style.display = 'none';
            }
        });

        sourceTypeSelect.addEventListener('change', (event) => {
            const selectedType = event.target.value;
            sourceLinkField.style.display = 'none';
            sourceUploadField.style.display = 'none';
            sourceTextField.style.display = 'none';

            if (selectedType === 'link') {
                sourceLinkField.style.display = 'block';
            } else if (selectedType === 'upload') {
                sourceUploadField.style.display = 'block';
            } else if (selectedType === 'text') {
                sourceTextField.style.display = 'block';
            }
        });
        // Trigger change once to show default field
        sourceTypeSelect.dispatchEvent(new Event('change'));

        // Handle Add Source Form Submission
        addSourceForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const currentNotebookId = addSourceForm.dataset.notebookId;
            const selectedSourceType = sourceTypeSelect.value;
            let payload = { notebook_id: currentNotebookId, source_type: selectedSourceType };

            if (selectedSourceType === 'link') {
                payload.url = document.getElementById('source-link').value.trim();
                if (!payload.url) {
                    showError('Link URL cannot be empty.');
                    return;
                }
            } else if (selectedSourceType === 'text') {
                payload.content = document.getElementById('source-text').value.trim();
                if (!payload.content) {
                    showError('Text content cannot be empty.');
                    return;
                }
            } else if (selectedSourceType === 'upload') {
                showWarning('File upload is not yet supported.');
                return; // Prevent submission for now
            }

            try {
                const response = await fetch('/api/sources', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(payload),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
                }

                const newSource = await response.json();
                console.log('Source added:', newSource);
                showSuccess('Source added successfully!');
                addSourceModal.style.display = 'none'; // Close modal
                displayNotebookDetails(currentNotebookId); // Refresh notebook details
            } catch (error) {
                console.error('Error adding source:', error);
                showError(`Failed to add source: ${error.message}`);
            }
        });

        // Add Note Modal Logic
        const addNoteBtn = document.getElementById('add-note-btn');
        const addNoteModal = document.getElementById('add-note-modal');
        const closeNoteModalButton = addNoteModal.querySelector('.close-button');
        const addNoteForm = document.getElementById('add-note-form');

        addNoteBtn.addEventListener('click', () => {
            addNoteModal.style.display = 'block';
            addNoteForm.dataset.notebookId = notebookId;
        });

        closeNoteModalButton.addEventListener('click', () => {
            addNoteModal.style.display = 'none';
        });

        window.addEventListener('click', (event) => {
            if (event.target == addNoteModal) {
                addNoteModal.style.display = 'none';
            }
        });

        // Handle Add Note Form Submission
        addNoteForm.addEventListener('submit', async (event) => {
            event.preventDefault();
            const currentNotebookId = addNoteForm.dataset.notebookId;
            const noteTitle = document.getElementById('note-title').value.trim();
            const noteContent = document.getElementById('note-content').value.trim();

            if (!noteContent) {
                showError('Note content cannot be empty.');
                return;
            }

            try {
                const response = await fetch('/api/notes', { // New endpoint for notes
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ notebook_id: currentNotebookId, title: noteTitle, content: noteContent }),
                });

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
                }

                const newNote = await response.json();
                console.log('Note added:', newNote);
                showSuccess('Note added successfully!');
                addNoteModal.style.display = 'none'; // Close modal
                document.getElementById('note-title').value = ''; // Clear form
                document.getElementById('note-content').value = ''; // Clear form
                displayNotebookDetails(currentNotebookId); // Refresh notebook details
            } catch (error) {
                console.error('Error adding note:', error);
                showError(`Failed to add note: ${error.message}`);
            }
        });


    } catch (error) {
        console.error('Error fetching notebook details:', error);
        mainContent.innerHTML = `<p style="color: red;">Error loading notebook details: ${error.message}</p><button onclick="window.location.reload()">Back to Notebooks</button>`;
    }
}

async function updateNotebook(notebookId, name, description, archived) {
    try {
        const response = await fetch(`/api/notebooks/${notebookId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, description, archived }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }

        showSuccess('Notebook updated successfully!');
        displayNotebookDetails(notebookId); // Refresh details
    } catch (error) {
        console.error('Error updating notebook:', error);
        showError(`Failed to update notebook: ${error.message}`);
    }
}

async function deleteNotebook(notebookId) {
    try {
        const response = await fetch(`/api/notebooks/${notebookId}`, {
            method: 'DELETE',
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(`HTTP error! status: ${response.status}, details: ${errorData.error || 'Unknown error'}`);
        }

        showSuccess('Notebook deleted successfully!');
        window.location.reload(); // Go back to the list
    } catch (error) {
        console.error('Error deleting notebook:', error);
        showError(`Failed to delete notebook: ${error.message}`);
    }
}

function setupSearchFunctionality() {
    const notebookListView = document.getElementById('notebook-list-view');
    const searchView = document.getElementById('search-view');
    const searchQueryInput = document.getElementById('search-query');
    const searchTypeRadios = document.querySelectorAll('input[name="search-type"]');
    const searchSourcesCheckbox = document.getElementById('search-sources');
    const searchNotesCheckbox = document.getElementById('search-notes');
    const performSearchBtn = document.getElementById('perform-search-btn');
    const searchResultsContainer = document.getElementById('search-results-container');

    // Add a button to switch to search view (e.g., in the main header or sidebar)
    // For now, let's add a simple button to the body for testing
    const toggleSearchBtn = document.createElement('button');
    toggleSearchBtn.textContent = 'Toggle Search View';
    toggleSearchBtn.style.position = 'fixed';
    toggleSearchBtn.style.top = '60px'; // Adjusted position
    toggleSearchBtn.style.right = '10px';
    toggleSearchBtn.style.padding = '10px';
    toggleSearchBtn.style.backgroundColor = '#f0ad4e';
    toggleSearchBtn.style.color = 'white';
    toggleSearchBtn.style.border = 'none';
    toggleSearchBtn.style.borderRadius = '5px';
    toggleSearchBtn.style.cursor = 'pointer';
    document.body.appendChild(toggleSearchBtn);

    toggleSearchBtn.addEventListener('click', () => {
        if (notebookListView.style.display !== 'none') {
            notebookListView.style.display = 'none';
            searchView.style.display = 'block';
            toggleSearchBtn.textContent = 'Back to Notebooks';
        } else {
            notebookListView.style.display = 'block';
            searchView.style.display = 'none';
            toggleSearchBtn.textContent = 'Toggle Search View';
            fetchNotebooks(); // Refresh notebooks when returning
        }
    });

    performSearchBtn.addEventListener('click', async () => {
        const keyword = searchQueryInput.value.trim();
        if (!keyword) {
            showWarning('Please enter a search query.');
            return;
        }

        const searchType = document.querySelector('input[name="search-type"]:checked').value;
        const searchSources = searchSourcesCheckbox.checked;
        const searchNotes = searchNotesCheckbox.checked;

        searchResultsContainer.innerHTML = `
            <div class="loading">
                <div class="loading-dots">
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                    <div class="loading-dot"></div>
                </div>
            </div>
        `;

        try {
            let url = '';
            if (searchType === 'text') {
                url = `/api/search/text?keyword=${encodeURIComponent(keyword)}&sources=${searchSources}&notes=${searchNotes}`;
            } else if (searchType === 'vector') {
                url = `/api/search/vector?keyword=${encodeURIComponent(keyword)}&sources=${searchSources}&notes=${searchNotes}`;
            }

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const results = await response.json();

            searchResultsContainer.innerHTML = ''; // Clear loading message

            if (results.length === 0) {
                searchResultsContainer.innerHTML = '<p>No results found.</p>';
                return;
            }

            results.forEach(item => {
                const resultElement = document.createElement('div');
                resultElement.className = 'search-result-card';
                resultElement.innerHTML = `
                    <h4>${item.title || 'No Title'} (Score: ${item.final_score ? item.final_score.toFixed(2) : 'N/A'})</h4>
                    <p>Type: ${item.type}</p>
                    <p>${item.content ? item.content.substring(0, 200) + '...' : 'No content preview.'}</p>
                    <button class="open-search-result-btn" data-id="${item.id}">Open</button>
                `;
                searchResultsContainer.appendChild(resultElement);
            });

            // Add event listeners for opening search results
            document.querySelectorAll('.open-search-result-btn').forEach(button => {
                button.addEventListener('click', (event) => {
                    const itemId = event.target.dataset.id;
                    // Determine if it's a source or note and display details
                    if (itemId.startsWith('source:')) {
                        displaySourceDetailsFromSearch(itemId); // Call new function
                    } else if (itemId.startsWith('note:')) {
                        displayNoteDetailsFromSearch(itemId); // Call new function
                    }
                });
            });

        } catch (error) {
            console.error('Error performing search:', error);
            searchResultsContainer.innerHTML = `<p style="color: red;">Error performing search: ${error.message}</p>`;
        }
    });
}

async function displaySourceDetailsFromSearch(sourceId) {
    const mainContent = document.querySelector('body');
    mainContent.innerHTML = `
        <h1>Loading Source...</h1>
        <p>ID: ${sourceId}</p>
    `;
    try {
        const response = await fetch(`/api/sources/${sourceId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const source = await response.json();

        mainContent.innerHTML = `
            <div class="notebook-detail-header">
                <h1>Source: ${source.title || 'No Title'}</h1>
                <button onclick="window.location.reload()">Back to Search</button>
            </div>
            <p>Created: ${new Date(source.created).toLocaleString()}</p>
            <p>Updated: ${new Date(source.updated).toLocaleString()}</p>
            <h3>Full Text</h3>
            <p>${source.full_text || 'No full text available.'}</p>
        `;
    } catch (error) {
        console.error('Error fetching source details:', error);
        mainContent.innerHTML = `<p style="color: red;">Error loading source details: ${error.message}</p><button onclick="window.location.reload()">Back to Search</button>`;
    }
}

async function displayNoteDetailsFromSearch(noteId) {
    const mainContent = document.querySelector('body');
    mainContent.innerHTML = `
        <h1>Loading Note...</h1>
        <p>ID: ${noteId}</p>
    `;
    try {
        const response = await fetch(`/api/notes/${noteId}`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        const note = await response.json();

        mainContent.innerHTML = `
            <div class="notebook-detail-header">
                <h1>Note: ${note.title || 'No Title'}</h1>
                <button onclick="window.location.reload()">Back to Search</button>
            </div>
            <p>Created: ${new Date(note.created).toLocaleString()}</p>
            <p>Updated: ${new Date(note.updated).toLocaleString()}</p>
            <h3>Content</h3>
            <p>${note.content || 'No content available.'}</p>
        `;
    } catch (error) {
        console.error('Error fetching note details:', error);
        mainContent.innerHTML = `<p style="color: red;">Error loading note details: ${error.message}</p><button onclick="window.location.reload()">Back to Search</button>`;
    }
}
