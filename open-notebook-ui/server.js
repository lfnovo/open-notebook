const express = require('express');
const path = require('path');

const app = express();
const port = 3000;

// Middleware to parse JSON request bodies
app.use(express.json());

// Serve static files from the 'public' directory
app.use(express.static(path.join(__dirname, 'public')));

const { spawn } = require('child_process');

// API endpoint to get all notebooks
app.get('/api/notebooks', (req, res) => {
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_notebooks.py')]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to fetch notebooks', details: error });
        }
        try {
            const trimmedData = data.trim();
            if (!trimmedData) {
                return res.json([]); // Return empty array if no data
            }
            // Split the output by newlines, filter out empty lines, and parse each line as a JSON object
            const notebooks = trimmedData.split('\n').filter(line => line.trim() !== '').map(line => JSON.parse(line));
            res.json(notebooks);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse notebooks data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to create a new notebook
app.post('/api/notebooks', (req, res) => {
    const { name, description } = req.body;

    if (!name) {
        return res.status(400).json({ error: 'Notebook name is required.' });
    }

    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'create_notebook.py')]);

    let data = '';
    let error = '';

    // Send data to Python script's stdin
    pythonProcess.stdin.write(JSON.stringify({ name, description }));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to create notebook', details: error });
        }
        try {
            const newNotebook = JSON.parse(data.trim());
            res.status(201).json(newNotebook);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse new notebook data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to get a single notebook's details
app.get('/api/notebooks/:id', (req, res) => {
    const notebookId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_notebook_details.py'), notebookId]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to fetch notebook details', details: error });
        }
        try {
            const notebookDetails = JSON.parse(data.trim());
            res.json(notebookDetails);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse notebook details data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to update a notebook
app.put('/api/notebooks/:id', (req, res) => {
    const notebookId = req.params.id;
    const { name, description, archived } = req.body;

    if (!name) {
        return res.status(400).json({ error: 'Notebook name is required.' });
    }

    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_notebook.py'), notebookId]);

    let data = '';
    let error = '';

    pythonProcess.stdin.write(JSON.stringify({ name, description, archived }));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to update notebook', details: error });
        }
        try {
            const updatedNotebook = JSON.parse(data.trim());
            res.json(updatedNotebook);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse updated notebook data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to delete a notebook
app.delete('/api/notebooks/:id', (req, res) => {
    const notebookId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'delete_notebook.py'), notebookId]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to delete notebook', details: error });
        }
        try {
            const trimmedData = data.trim();
            if (!trimmedData) {
                // If no data, assume success for delete or handle as specific error
                return res.status(200).json({ success: true, message: "Operation completed with no data returned." });
            }
            const result = JSON.parse(trimmedData);
            res.json(result);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse delete result', details: e.message, rawData: data });
        }
    });
});

// API endpoint to add a new source
app.post('/api/sources', (req, res) => {
    const { notebook_id, source_type, content, url } = req.body;

    if (!notebook_id || !source_type) {
        return res.status(400).json({ error: 'Notebook ID and source type are required.' });
    }

    // For now, handle text and link types. File upload will be more complex.
    if (source_type === 'upload') {
        return res.status(400).json({ error: 'File upload not yet implemented for sources.' });
    }

    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'add_source.py')]);

    let data = '';
    let error = '';

    pythonProcess.stdin.write(JSON.stringify({ notebook_id, source_type, content, url }));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to add source', details: error });
        }
        try {
            const newSource = JSON.parse(data.trim());
            res.status(201).json(newSource);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse new source data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to add a new note
app.post('/api/notes', (req, res) => {
    const { notebook_id, title, content } = req.body;

    if (!notebook_id || !content) {
        return res.status(400).json({ error: 'Notebook ID and note content are required.' });
    }

    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'add_note.py')]);

    let data = '';
    let error = '';

    pythonProcess.stdin.write(JSON.stringify({ notebook_id, title, content }));
    pythonProcess.stdin.end();

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to add note', details: error });
        }
        try {
            const newNote = JSON.parse(data.trim());
            res.status(201).json(newNote);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse new note data', details: e.message, rawData: data });
        }
    });
});

// API endpoint for text search
app.get('/api/search/text', (req, res) => {
    const { keyword, limit, sources, notes } = req.query;

    if (!keyword) {
        return res.status(400).json({ error: 'Search keyword is required.' });
    }

    const pythonProcess = spawn('uv', [
        'run',
        'python3',
        path.join(__dirname, 'backend_api', 'text_search.py'),
        keyword,
        limit || '100',
        sources || 'true',
        notes || 'true'
    ]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to perform text search', details: error });
        }
        try {
            const searchResults = JSON.parse(data.trim());
            res.json(searchResults);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse text search results', details: e.message, rawData: data });
        }
    });
});

// API endpoint for vector search
app.get('/api/search/vector', (req, res) => {
    const { keyword, limit, sources, notes, min_score } = req.query;

    if (!keyword) {
        return res.status(400).json({ error: 'Search keyword is required.' });
    }

    const pythonProcess = spawn('uv', [
        'run',
        'python3',
        path.join(__dirname, 'backend_api', 'vector_search.py'),
        keyword,
        limit || '100',
        sources || 'true',
        notes || 'true',
        min_score || '0.2'
    ]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to perform vector search', details: error });
        }
        try {
            const searchResults = JSON.parse(data.trim());
            res.json(searchResults);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse vector search results', details: e.message, rawData: data });
        }
    });
});

// API endpoint to get a single source's details
app.get('/api/sources/:id', (req, res) => {
    const sourceId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_source_details.py'), sourceId]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to fetch source details', details: error });
        }
        try {
            const sourceDetails = JSON.parse(data.trim());
            res.json(sourceDetails);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse source details data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to get a single note's details
app.get('/api/notes/:id', (req, res) => {
    const noteId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_note_details.py'), noteId]);

    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: 'Failed to fetch note details', details: error });
        }
        try {
            const noteDetails = JSON.parse(data.trim());
            res.json(noteDetails);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: 'Failed to parse note details data', details: e.message, rawData: data });
        }
    });
});

// API endpoint to get all models
app.get('/api/models/all', (req, res) => {
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_models.py'), 'all']);
    handlePythonProcess(pythonProcess, res, 'Failed to fetch all models');
});

// API endpoint to get models by type
app.get('/api/models/by_type/:type', (req, res) => {
    const modelType = req.params.type;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_models.py'), 'by_type', modelType]);
    handlePythonProcess(pythonProcess, res, `Failed to fetch models of type ${modelType}`);
});

// API endpoint to get default models
app.get('/api/models/defaults', (req, res) => {
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_models.py'), 'defaults']);
    handlePythonProcess(pythonProcess, res, 'Failed to fetch default models');
});

// API endpoint to get available providers
app.get('/api/models/providers', (req, res) => {
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_models.py'), 'providers']);
    handlePythonProcess(pythonProcess, res, 'Failed to fetch available providers');
});

// Helper function to handle Python process output
function handlePythonProcess(pythonProcess, res, errorMessage) {
    let data = '';
    let error = '';

    pythonProcess.stdout.on('data', (chunk) => {
        data += chunk.toString();
    });

    pythonProcess.stderr.on('data', (chunk) => {
        error += chunk.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}, error: ${error}`);
            return res.status(500).json({ error: errorMessage, details: error });
        }
        try {
            const result = JSON.parse(data.trim());
            if (result && result.error) { // Check if Python script returned an error object
                return res.status(500).json({ error: errorMessage, details: result.error });
            }
            res.json(result);
        } catch (e) {
            console.error('Failed to parse Python script output:', e, 'Raw data:', data);
            res.status(500).json({ error: `${errorMessage} - Failed to parse data`, details: e.message, rawData: data });
        }
    });
}

// API endpoint to add a new model
app.post('/api/models', (req, res) => {
    const { name, provider, type } = req.body;
    if (!name || !provider || !type) {
        return res.status(400).json({ error: 'Model name, provider, and type are required.' });
    }
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'add_model.py')]);
    pythonProcess.stdin.write(JSON.stringify({ name, provider, type }));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to add model');
});

// API endpoint to delete a model
app.delete('/api/models/:id', (req, res) => {
    const modelId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'delete_model.py'), modelId]);
    handlePythonProcess(pythonProcess, res, 'Failed to delete model');
});

// API endpoint to update default models
app.put('/api/models/defaults', (req, res) => {
    const modelUpdates = req.body;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_default_models.py')]);
    pythonProcess.stdin.write(JSON.stringify(modelUpdates));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to update default models');
});

// API endpoint to get all transformations or default prompts
app.get('/api/transformations/:action', (req, res) => {
    const action = req.params.action;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_transformations.py'), action]);
    handlePythonProcess(pythonProcess, res, `Failed to fetch ${action} transformations`);
});

// API endpoint to add a new transformation
app.post('/api/transformations', (req, res) => {
    const { name, title, description, prompt, apply_default } = req.body;
    if (!name || !title || !description || !prompt) {
        return res.status(400).json({ error: 'Name, title, description, and prompt are required.' });
    }
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'add_transformation.py')]);
    pythonProcess.stdin.write(JSON.stringify({ name, title, description, prompt, apply_default }));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to add transformation');
});

// API endpoint to update a transformation
app.put('/api/transformations/:id', (req, res) => {
    const transformationId = req.params.id;
    const { name, title, description, prompt, apply_default } = req.body;
    if (!name || !title || !description || !prompt) {
        return res.status(400).json({ error: 'Name, title, description, and prompt are required.' });
    }
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_transformation.py'), transformationId]);
    pythonProcess.stdin.write(JSON.stringify({ name, title, description, prompt, apply_default }));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to update transformation');
});

// API endpoint to delete a transformation
app.delete('/api/transformations/:id', (req, res) => {
    const transformationId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'delete_transformation.py'), transformationId]);
    handlePythonProcess(pythonProcess, res, 'Failed to delete transformation');
});

// API endpoint to get a single transformation's details
app.get('/api/transformations/:id', (req, res) => {
    const transformationId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_transformation_details.py'), transformationId]);
    handlePythonProcess(pythonProcess, res, 'Failed to fetch transformation details');
});

// API endpoint to update default prompts
app.put('/api/transformations/defaults', (req, res) => {
    const { transformation_instructions } = req.body;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_default_prompts.py')]);
    pythonProcess.stdin.write(JSON.stringify({ transformation_instructions }));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to update default prompts');
});

// API endpoint to get podcast configs or episodes
app.get('/api/podcasts/:action', (req, res) => {
    const action = req.params.action;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_podcast_configs.py'), action]);
    handlePythonProcess(pythonProcess, res, `Failed to fetch podcast ${action}`);
});

// API endpoint to add a new podcast config
app.post('/api/podcasts/configs', (req, res) => {
    const configData = req.body;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'add_podcast_config.py')]);
    pythonProcess.stdin.write(JSON.stringify(configData));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to add podcast configuration');
});

// API endpoint to update a podcast config
app.put('/api/podcasts/configs/:id', (req, res) => {
    const configId = req.params.id;
    const configData = req.body;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_podcast_config.py'), configId]);
    pythonProcess.stdin.write(JSON.stringify(configData));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to update podcast configuration');
});

// API endpoint to delete a podcast config
app.delete('/api/podcasts/configs/:id', (req, res) => {
    const configId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'delete_podcast_config.py'), configId]);
    handlePythonProcess(pythonProcess, res, 'Failed to delete podcast configuration');
});

// API endpoint to generate a podcast episode
app.post('/api/podcasts/generate-episode', (req, res) => {
    const { config_id, episode_name, text, instructions, longform, chunks, min_chunk_size } = req.body;
    if (!config_id || !episode_name || !text) {
        return res.status(400).json({ error: 'Config ID, episode name, and text are required for episode generation.' });
    }
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'generate_podcast_episode.py')]);
    pythonProcess.stdin.write(JSON.stringify({ config_id, episode_name, text, instructions, longform, chunks, min_chunk_size }));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to generate podcast episode');
});

// API endpoint to delete a podcast episode
app.delete('/api/podcasts/episodes/:id', (req, res) => {
    const episodeId = req.params.id;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'delete_podcast_episode.py'), episodeId]);
    handlePythonProcess(pythonProcess, res, 'Failed to delete podcast episode');
});

// API endpoint to get content settings
app.get('/api/settings/content', (req, res) => {
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'get_content_settings.py')]);
    handlePythonProcess(pythonProcess, res, 'Failed to fetch content settings');
});

// API endpoint to update content settings
app.put('/api/settings/content', (req, res) => {
    const settingsUpdates = req.body;
    const pythonProcess = spawn('uv', ['run', 'python3', path.join(__dirname, 'backend_api', 'update_content_settings.py')]);
    pythonProcess.stdin.write(JSON.stringify(settingsUpdates));
    pythonProcess.stdin.end();
    handlePythonProcess(pythonProcess, res, 'Failed to update content settings');
});

app.get('/api/hello', (req, res) => {
    res.json({ message: 'Hello from Node.js backend!' });
});

// Serve index.html for the root path
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

app.listen(port, () => {
    console.log(`Node.js frontend server listening at http://localhost:${port}`);
});
