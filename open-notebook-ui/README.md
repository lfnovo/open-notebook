## Open Notebook UI

This document provides a comprehensive overview of the Node.js-based frontend for the Open Notebook application. It details the project's structure, functionality, and setup, offering a clear guide for developers and contributors.

### Introduction

The Open Notebook UI is a user-friendly interface built with Node.js, HTML, CSS, and JavaScript. It replaces the original Streamlit frontend, offering a more traditional web application experience. This UI allows users to interact with the core features of the Open Notebook, including managing notebooks, sources, podcasts, and transformations.

### File Structure

The `open-notebook-ui` directory contains all the files necessary for the frontend to run. Here's a breakdown of the key files and directories:

- **`server.js`**: This is the entry point of the application. It sets up an Express server to handle API requests and serve the static files from the `public` directory.

- **`package.json` and `package-lock.json`**: These files manage the project's dependencies and scripts.

- **`backend_api/`**: This directory contains Python scripts that act as a bridge between the Node.js frontend and the application's core logic. Each script corresponds to a specific backend action, such as adding a notebook or fetching data.

- **`public/`**: This directory holds all the static assets for the frontend, including HTML, CSS, and JavaScript files. These files are served directly to the user's browser.

- **`data/`**: This directory is used for data storage, including the SQLite database and any uploaded files.

### Backend API

The `backend_api` directory is crucial for the functioning of the UI. It contains a collection of Python scripts that are executed by the Node.js server to perform backend operations. This approach allows the frontend to remain decoupled from the core Python application while still being able to access its features.

When the frontend needs to perform an action, such as creating a new notebook, it sends a request to the Node.js server. The server then executes the corresponding Python script in the `backend_api` directory, passing any necessary parameters. The Python script interacts with the Open Notebook's database and returns the result to the Node.js server, which then forwards it to the frontend.

### Public Directory

The `public` directory contains the user-facing part of the application. Here's a look at some of the important files:

- **`index.html`**: The main dashboard, providing an overview of the user's notebooks and recent activity.
- **`notebooks.html`**: Displays a list of all notebooks and allows for the creation of new ones.
- **`notebook.html`**: The detailed view of a single notebook, showing its sources and notes.
- **`podcasts.html`**: Manages podcast configurations and generated episodes.
- **`transformations.html`**: Handles different data transformations that can be applied to sources.
- **`models.html`**: Manages the AI models used for various tasks.
- **`settings.html`**: Contains application-wide settings and configurations.

Each HTML file is accompanied by a corresponding CSS file for styling and a JavaScript file for client-side logic. For example, `notebooks.js` contains the code to fetch and display the list of notebooks, while `notebook.js` handles the interactions within a single notebook.

### How It Works

The Open Notebook UI operates as a classic client-server application:

1.  **Client-Side**: The user interacts with the HTML, CSS, and JavaScript files running in their browser. When an action is performed (e.g., clicking a button), the client-side JavaScript sends a request to the Node.js server.

2.  **Server-Side (Node.js)**: The Express server, defined in `server.js`, listens for incoming requests from the client. When a request is received, the server determines which backend operation needs to be performed and executes the appropriate Python script from the `backend_api` directory.

3.  **Backend (Python)**: The Python script runs, interacting with the Open Notebook's core logic and database. It then returns the result of the operation to the Node.js server.

4.  **Response**: The Node.js server sends the result back to the client-side JavaScript, which then updates the UI to reflect the changes.

#### API Endpoints

The `backend_api` directory contains a comprehensive set of scripts for interacting with the Open Notebook's core functionality. Here is a complete list of the available endpoints and their purposes:

##### Notebook Management
- **`create_notebook.py`**: Creates a new notebook.
- **`get_notebooks.py`**: Retrieves a list of all notebooks.
- **`get_notebook_details.py`**: Fetches the details of a specific notebook.
- **`update_notebook.py`**: Updates the properties of a notebook.
- **`delete_notebook.py`**: Removes a notebook from the system.

##### Note and Source Management
- **`add_note.py`**: Adds a new note to a notebook.
- **`get_note_details.py`**: Retrieves the details of a specific note.
- **`add_source.py`**: Adds a new data source (e.g., URL, file) to a notebook.
- **`get_source_details.py`**: Fetches the details of a specific source.

##### Podcast Management
- **`add_podcast_config.py`**: Creates a new podcast configuration.
- **`get_podcast_configs.py`**: Retrieves all podcast configurations.
- **`update_podcast_config.py`**: Updates an existing podcast configuration.
- **`delete_podcast_config.py`**: Deletes a podcast configuration.
- **`generate_podcast_episode.py`**: Generates a new podcast episode based on a configuration.
- **`delete_podcast_episode.py`**: Deletes a podcast episode.

##### Transformation Management
- **`add_transformation.py`**: Adds a new data transformation.
- **`get_transformations.py`**: Retrieves all available transformations.
- **`get_transformation_details.py`**: Fetches the details of a specific transformation.
- **`update_transformation.py`**: Updates an existing transformation.
- **`delete_transformation.py`**: Deletes a transformation.

##### Model and Settings Management
- **`add_model.py`**: Adds a new AI model to the system.
- **`get_models.py`**: Retrieves all available AI models.
- **`delete_model.py`**: Removes an AI model.
- **`get_content_settings.py`**: Retrieves the current content settings.
- **`update_content_settings.py`**: Updates the content settings.
- **`update_default_models.py`**: Sets the default models for various tasks.
- **`update_default_prompts.py`**: Sets the default prompts for AI interactions.

##### Search Functionality
- **`text_search.py`**: Performs a text-based search across all notebooks.
- **`vector_search.py`**: Performs a vector-based similarity search.

#### UI Components

The user interface is designed to be intuitive and easy to navigate. Here's a closer look at the main components:

- **Dashboard (`index.html`)**: The landing page of the application. It provides a high-level overview of the user's work, including a list of recent notebooks and quick access to common actions.

- **Notebooks Page (`notebooks.html`)**: This page displays a comprehensive list of all the user's notebooks. From here, you can create new notebooks, open existing ones, or delete those that are no longer needed.

- **Notebook Detail Page (`notebook.html`)**: When you open a notebook, you are taken to this detailed view. It shows all the sources and notes associated with the notebook, allowing you to add new content, view existing entries, and manage the notebook's structure.

- **Podcasts Page (`podcasts.html`)**: This section is dedicated to managing podcasts. You can create new podcast configurations, view and listen to generated episodes, and manage your podcast settings.

- **Transformations Page (`transformations.html`)**: Here, you can manage the data transformations that can be applied to your sources. This allows you to process and clean your data in various ways before it is used by the AI models.

- **Models Page (`models.html`)**: This page provides an interface for managing the AI models used by the application. You can add new models, view existing ones, and set the default models for different tasks.

- **Settings Page (`settings.html`)**: This is where you can configure the application's overall settings, such as default prompts, content settings, and other preferences.

### How to Run

To run the Open Notebook UI, you need to have Node.js and npm installed.

1.  **Navigate to the `open-notebook-ui` directory**:
    ```bash
    cd open-notebook-ui
    ```

2.  **Install the dependencies**:
    ```bash
    npm install
    ```

3.  **Start the server**:
    ```bash
    npm run dev
    ```

The application will then be available at `http://localhost:3000` in your web browser.

### API Testing

The `api_sanity_check.sh` script is included to provide a quick way to test the functionality of the backend API. This script sends a series of `curl` requests to the various API endpoints to ensure they are responding correctly.

#### How to Run the Tests

To run the API sanity check, make sure the server is running, and then execute the following command in your terminal:

```bash
bash api_sanity_check.sh
```

The script will output the results of each test, indicating whether it was successful or not. This is a useful tool for verifying that the backend is working as expected after making changes to the code.
