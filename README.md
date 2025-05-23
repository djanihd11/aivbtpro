# VectorBTPro AI Expert Agent

## Overview

The VectorBTPro AI Expert Agent is a Dockerized JupyterLab environment designed to supercharge your quantitative trading research and strategy development with `vectorbtpro`. It integrates a custom AI assistant powered by Google's Gemini model and a Retrieval Augmented Generation (RAG) system. This agent has been trained on your provided `vectorbtpro` documentation, allowing it to answer questions, generate `vectorbtpro`-specific Python code, and assist with various analytical tasks directly within JupyterLab.

## Features

*   **Dockerized JupyterLab:** Pre-configured environment with JupyterLab, Python 3.9, and common data science libraries.
*   **VectorBTPro Integration:** Ready for your specific `vectorbtpro` library to be built into the image.
*   **Integrated AI Agent:** A FastAPI backend serves the custom AI agent, accessible within JupyterLab.
*   **Google Gemini Model:** Leverages the capabilities of the Gemini family of models for response generation.
*   **RAG System:** The agent uses a knowledge base built from your local `vectorbtpro` documentation (markdown files) to provide contextually relevant answers.
*   **Jupyter Magic Commands:**
    *   `%vectorbt_init YOUR_GEMINI_API_KEY [docs_path]`: Initializes the AI agent.
    *   `%%vectorbt_expert`: Cell magic to query the agent.
    *   `%vectorbt_status`: Checks the agent's status.
*   **Interactive Chat Widget:** A user-friendly chat interface within JupyterLab for seamless interaction with the agent.
*   **Automated Code Generation:** Get help generating `vectorbtpro` Python code for data analysis, backtesting, and visualization.
*   **Pre-configured Dependencies:** Includes `TA-Lib` and other common `vectorbtpro` dependencies as specified in the Dockerfile.
*   **Jupyter AI (Bonus):** The environment also includes `jupyter-ai`, providing general AI chat capabilities alongside the specialized VectorBTPro agent.

## Project Structure

```
.
├── agent_system/         # FastAPI backend and JupyterLab extension code
│   ├── __init__.py
│   ├── agent_backend.py  # Core logic for the AI agent, RAG, and Gemini integration
│   └── jupyter_extension.py # IPython magics and chat widget
├── documentation/        # User-provided: Your vectorbtpro .md documentation files for RAG
├── notebooks/            # User-provided (and welcome notebook): For your Jupyter notebooks
├── strategies/           # User-provided: For storing your trading strategy files
├── vectorbtpro/          # User-provided: Your vectorbtpro library source code (to be copied here)
├── Dockerfile            # Defines the Docker image
├── pyproject.toml        # User-provided: Your vectorbtpro pyproject.toml (to be copied here)
├── LICENSE               # User-provided: Your vectorbtpro LICENSE file (to be copied here, if needed for install)
├── README.md             # This project's README file. (Your vectorbtpro README.md is also copied if needed for install)
└── start.sh              # Entrypoint script for the Docker container
```

## Prerequisites

*   **Docker:** Docker installed and running on your system. ([Installation Guide](https://docs.docker.com/get-docker/))
*   **Gemini API Key:** An active API key for Google's Gemini models. ([Get an API Key](https://ai.google.dev/))
*   **Your `vectorbtpro` Source Code:** The complete source code for your `vectorbtpro` library.
*   **Your `vectorbtpro` Documentation:** Documentation files for your library, preferably in Markdown (`.md`) format.

## Setup Instructions

### 1. Clone the Repository (or Download Files)
If this project is hosted in a Git repository, clone it:
```bash
git clone <repository_url>
cd <repository_directory_name>
```
If you have downloaded it as a ZIP, extract it and navigate into the project's root directory.

### 2. Add Your VectorBTPro Source Code
This setup requires your specific `vectorbtpro` library to be built into the Docker image.
*   Create a directory named `vectorbtpro` in the root of this project (if it doesn't exist).
*   Copy your **entire** `vectorbtpro` library source code into this newly created `vectorbtpro/` directory.
*   Copy your main `pyproject.toml` file (the one used for `pip install .` of your `vectorbtpro` library) into the root of this project.
*   If your `vectorbtpro` installation process (via `pip install .`) requires your library's `LICENSE` or `README.md` files to be present in the root of the installation directory, copy those files into the root of this project as well.

The Docker build process (`COPY vectorbtpro/ ...`, `COPY pyproject.toml ...`, etc., in `Dockerfile`) uses these files to install your version of `vectorbtpro` within the Docker image.

### 3. Add Your VectorBTPro Documentation for RAG
The AI agent builds its knowledge base from your `vectorbtpro` documentation.
*   Place all your `vectorbtpro` documentation files (they **must be `.md` Markdown files**) into the `documentation/` directory in the root of this project.
*   The agent will recursively scan this directory for markdown files during its initialization. The more comprehensive your markdown documentation, the better the agent's responses will be.

### 4. Configure Environment Variables
The primary environment variable you **must** set when running the Docker container is `GEMINI_API_KEY`. This is your personal API key for Google's Gemini service.

## Build and Run the Docker Container

### Build the Image
Open your terminal in the root directory of this project (where the `Dockerfile` is located) and run:
```bash
docker build -t vectorbtpro-expert .
```
This command builds the Docker image and tags it as `vectorbtpro-expert`.

### Run the Container
Once the image is successfully built, run the container using the following command:
```bash
docker run -p 8888:8888 -p 8000:8000 \
  -e GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE" \
  -v "$(pwd)/documentation":/home/jovyan/work/documentation \
  -v "$(pwd)/notebooks":/home/jovyan/work/notebooks \
  -v "$(pwd)/strategies":/home/jovyan/work/strategies \
  --name vectorbtpro-ai-expert \
  vectorbtpro-expert
```

**Replace `"YOUR_GEMINI_API_KEY_HERE"` with your actual Gemini API key.**

**Explanation of `docker run` options:**
*   `-p 8888:8888`: Maps port 8888 on your host machine to port 8888 in the container (for JupyterLab).
*   `-p 8000:8000`: Maps port 8000 on your host to port 8000 in the container (for the AI agent backend).
*   `-e GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"`: **Crucial!** Sets your Gemini API key as an environment variable inside the container.
*   `-v "$(pwd)/documentation":/home/jovyan/work/documentation`: Mounts your local `documentation` directory (containing your `.md` files) into the container at `/home/jovyan/work/documentation`. This allows the agent to access your docs for RAG, and you can update them locally without rebuilding the image (though you might need to re-initialize the agent).
*   `-v "$(pwd)/notebooks":/home/jovyan/work/notebooks`: Mounts your local `notebooks` directory. This is where your Jupyter notebooks will be saved and persisted across container restarts. The Welcome Notebook will also be generated here.
*   `-v "$(pwd)/strategies":/home/jovyan/work/strategies`: Mounts your local `strategies` directory. This is a suggested location for persisting any trading strategy files you develop.
*   `--name vectorbtpro-ai-expert`: Assigns a convenient name to your running container, making it easier to manage (e.g., `docker stop vectorbtpro-ai-expert`).
*   `vectorbtpro-expert`: The name of the Docker image to run (which you built in the previous step).

## Using the VectorBTPro AI Expert

1.  **Access JupyterLab:** Open your web browser and navigate to `http://localhost:8888`.
2.  **Welcome Notebook:** In the JupyterLab file browser on the left, navigate into the `notebooks/` directory. Open the `Welcome_VectorBTPro_Expert.ipynb` notebook. This notebook provides initial guidance and runnable cells to get you started.

3.  **Initialization (Important!):**
    *   The agent backend attempts to auto-initialize on startup if the `GEMINI_API_KEY` environment variable was correctly passed during `docker run`.
    *   However, to ensure the agent is ready for your session, or if you wish to re-initialize (e.g., after updating documentation or to use a different API key for the session), run the following in a notebook cell:
      ```python
      %vectorbt_init YOUR_GEMINI_API_KEY_HERE
      ```
      (Replace `YOUR_GEMINI_API_KEY_HERE` with your actual key if you didn't set it as an environment variable or want to override it for the session).
    *   The agent will then load and process documentation from the mounted `documentation/` folder (specifically, `/home/jovyan/work/documentation` inside the container, which is mapped from your local `./documentation` folder).
    *   You can check the status of the initialization with `%vectorbt_status`.

4.  **Using Magic Commands:**
    *   **Ask a question or request code (`%%vectorbt_expert` cell magic):**
      Type `%%vectorbt_expert` at the beginning of a cell, then on the next lines, type your question.
      ```python
      %%vectorbt_expert
      How do I download Bitcoin (BTC-USD) price data for the last 90 days 
      using vectorbtpro and then calculate and plot its 20-day Simple Moving Average?
      ```
    *   **Check agent status (`%vectorbt_status` line magic):**
      ```python
      %vectorbt_status
      ```

5.  **Using the Interactive Chat Widget:**
    *   For a more conversational experience, run the following in a notebook cell to display the chat widget:
      ```python
      from agent_system.jupyter_extension import display_vectorbt_expert_widget
      display_vectorbt_expert_widget()
      ```
    *   This will render a chat interface where you can type your questions and receive answers. Code snippets provided by the agent in the widget will have an "Execute Code" button.

## Troubleshooting

*   **"Cannot connect to agent backend" / Errors in magic commands or widget:**
    *   Ensure the Docker container is running: `docker ps`. You should see `vectorbtpro-ai-expert` in the list with status "Up".
    *   Check the container logs for errors: `docker logs vectorbtpro-ai-expert`. Look for messages from Uvicorn (agent backend, usually on port 8000) or Jupyter (port 8888).
*   **"Agent not initialized" / "GEMINI_API_KEY not found" / No response from agent:**
    *   Make sure you have run `%vectorbt_init YOUR_GEMINI_API_KEY` in your notebook session, or that the `GEMINI_API_KEY` environment variable was correctly passed in your `docker run` command.
    *   Check the container logs (`docker logs vectorbtpro-ai-expert`). The agent backend should log whether it found the API key and the status of its initialization attempt.
*   **Documentation not found / Agent responses lack specific knowledge / Low document count in status:**
    *   Verify that your `.md` documentation files are directly inside the `documentation/` directory on your host machine (the one you mounted).
    *   Ensure the volume mount `-v "$(pwd)/documentation":/home/jovyan/work/documentation` in the `docker run` command is correct and points to your local documentation directory.
    *   The agent initialization log (seen after `%vectorbt_init` or in container logs on startup) should indicate how many document chunks were found and processed from the documentation path.
*   **Permission errors for mounted volumes (e.g., `EACCES`):**
    *   Ensure Docker has the necessary permissions to read from (and write to, for `notebooks` and `strategies`) the directories you are mounting from your host system. This can sometimes be an issue depending on your OS and Docker setup (e.g., SELinux on Linux).
    *   The `start.sh` script and Dockerfile attempt to manage permissions for the `jovyan` user within the container, but host path permissions are also important.

## Development Notes (Optional)

*   The AI agent's FastAPI backend is accessible at `http://localhost:8000` on your host machine. You can explore its API documentation at `http://localhost:8000/docs` if you wish to understand its capabilities directly.
*   **Key files for understanding and extending the system:**
    *   `Dockerfile`: Defines the Docker image, system dependencies, Python packages, and setup.
    *   `start.sh`: The container's entrypoint script. It initializes directories, deploys the Jupyter extension, starts the agent backend, and launches JupyterLab.
    *   `agent_system/agent_backend.py`: Contains the core logic for the AI agent, including the RAG implementation (ChromaDB, sentence transformers), Gemini model interaction, and the FastAPI application.
    *   `agent_system/jupyter_extension.py`: Implements the IPython magic commands (`%vectorbt_init`, `%%vectorbt_expert`, etc.) and the interactive ipywidgets-based chat widget.

---

Happy Quant Trading with your VectorBTPro AI Expert Agent!
```
