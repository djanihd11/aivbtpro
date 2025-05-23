#!/bin/bash
set -e

echo "Container starting..."

# Define Environment Variables (with defaults)
export DOCS_PATH=${DOCS_PATH:-"/home/jovyan/work/documentation"}
export KB_PATH=${KB_PATH:-"/home/jovyan/work/knowledge_base"} # Used by agent_backend.py for ChromaDB
export NOTEBOOKS_PATH=${NOTEBOOKS_PATH:-"/home/jovyan/work/notebooks"}
export STRATEGIES_PATH=${STRATEGIES_PATH:-"/home/jovyan/work/strategies"}
# GEMINI_API_KEY is read directly by the agent backend from the environment

echo "--- Environment Configuration ---"
echo "User: $(whoami)"
echo "Home: ${HOME}"
echo "DOCS_PATH: ${DOCS_PATH}"
echo "KB_PATH: ${KB_PATH}"
echo "NOTEBOOKS_PATH: ${NOTEBOOKS_PATH}"
echo "STRATEGIES_PATH: ${STRATEGIES_PATH}"
echo "GEMINI_API_KEY: (hidden, will be used by backend if set)"
echo "PYTHONPATH: ${PYTHONPATH}"
echo "-------------------------------"

# Create working directories
echo "Creating working directories..."
mkdir -p "${DOCS_PATH}"
mkdir -p "${KB_PATH}"
mkdir -p "${NOTEBOOKS_PATH}"
mkdir -p "${STRATEGIES_PATH}"
# Ensure the .ipython startup directory exists for the jovyan user
mkdir -p "/home/jovyan/.ipython/profile_default/startup/"

echo "Directories created."
echo "Ensuring correct ownership of /home/jovyan/work and subdirectories..."
# Ensure jovyan user owns the work directory and its contents, useful if volumes are mounted as root
# sudo chown -R ${NB_UID}:${NB_GID} /home/jovyan/work # This is usually handled by base image or Dockerfile

# Copy Jupyter Extension to IPython Startup directory
echo "Deploying JupyterLab extension for auto-loading..."
cp /home/jovyan/agent_system/jupyter_extension.py "/home/jovyan/.ipython/profile_default/startup/00-vectorbt-expert-startup.py"
# Ensure the startup script is readable by the user
chown ${NB_UID}:${NB_GID} "/home/jovyan/.ipython/profile_default/startup/00-vectorbt-expert-startup.py"
echo "JupyterLab extension deployed."

# Generate Welcome Notebook
WELCOME_NOTEBOOK_PATH="${NOTEBOOKS_PATH}/Welcome_VectorBTPro_Expert.ipynb" # Changed name slightly for clarity
echo "Generating Welcome Notebook at ${WELCOME_NOTEBOOK_PATH}..."

cat << EOF > "${WELCOME_NOTEBOOK_PATH}"
{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Welcome to the VectorBTPro Expert Agent!\\n",
    "\\n",
    "This environment is configured to help you leverage AI for your quantitative trading tasks with `vectorbtpro`.\\n",
    "\\n",
    "**Key Components:**\\n",
    "* **JupyterLab:** Your interactive development environment.\\n",
    "* **VectorBTPro Expert Agent:** An AI assistant (powered by Gemini) knowledgeable about `vectorbtpro`. You can interact with it via magic commands or a chat widget.\\n",
    "* **Pre-configured Backend:** The agent's backend service is running in this container."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 🚀 Step 1: Initialize the Agent\\n",
    "\\n",
    "Before you can use the agent, you **must** initialize it with your Gemini API Key. This tells the backend which API key to use for its Large Language Model calls.\\n",
    "\\n",
    "Run the following command in a code cell. **Replace `YOUR_GEMINI_API_KEY` with your actual key.**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {
    "tags": []
   },
   "outputs": [],
   "source": [
    "# Replace with your actual Gemini API Key and run this cell!\n",
    "# For example: %vectorbt_init AIzaSy*******************\n",
    "%vectorbt_init YOUR_GEMINI_API_KEY"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "If your `vectorbtpro` documentation is in a custom location *within the Docker container* that the agent backend should use for its knowledge base, you can specify it (though the default `/home/jovyan/vectorbtpro/docs` is usually correct for this setup):\\n",
    "```python\\n",
    "# %vectorbt_init YOUR_GEMINI_API_KEY /path/to/your/vectorbtpro/docs\\n",
    "```\\n",
    "You should see a confirmation message from the agent once initialization is complete. You can also check the agent's status anytime with `%vectorbt_status`."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "%vectorbt_status"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 💬 Step 2: Using the Agent\\n",
    "\\n",
    "Once initialized, you can interact with the agent in two ways:"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### A. Via Magic Command (`%%vectorbt_expert`)\\n",
    "\\n",
    "Use the `%%vectorbt_expert` cell magic to ask questions or request code related to `vectorbtpro`. The agent will provide a response, often including runnable code snippets.\\n",
    "\\n",
    "**Example:**"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "%%vectorbt_expert\n",
    "How do I download BTC/USDT price data for the last 30 days using vectorbtpro and plot it?"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### B. Via Interactive Chat Widget\\n",
    "\\n",
    "For a more conversational experience, you can use the chat widget. The JupyterLab extension that provides the magic commands also includes a function to display this widget.\\n",
    "\\n",
    "The agent extension (including magics and widget capabilities) should be auto-loaded when your Jupyter kernel starts, thanks to the setup in this container. If you encounter issues with `%vectorbt_init` or other magics not being recognized, ensure the kernel has fully started or try restarting it."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "# The agent_system.jupyter_extension should be auto-loaded by IPython.\n",
    "# If you suspect it's not (e.g., %vectorbt_init does nothing), you can try uncommenting the next line:\n",
    "# %load_ext agent_system.jupyter_extension\n",
    "\n",
    "# To display the chat widget, run this cell:\n",
    "from agent_system.jupyter_extension import display_vectorbt_expert_widget\n",
    "display_vectorbt_expert_widget()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 💡 Tips for Effective Use\\n",
    "\\n",
    "* **Be specific:** The more detailed your question, the better the agent can assist you.\\n",
    "* **Provide context:** If you're working on existing code, share relevant snippets.\\n",
    "* **Iterate:** If the first answer isn't perfect, refine your question or ask for clarification.\\n",
    "* **Review code:** Always review and understand any code provided by the agent before executing it, especially if it involves financial operations or API keys."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Next Steps\\n",
    "\\n",
    "1.  **Initialize the agent** in the code cell under \"Step 1\".\\n",
    "2.  Try the **example query** using `%%vectorbt_expert`.\\n",
    "3.  Launch the **chat widget** and ask more questions!\\n",
    "\\n",
    "Happy coding!"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3 (ipykernel)",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.18"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 5
}
EOF
chown ${NB_UID}:${NB_GID} "${WELCOME_NOTEBOOK_PATH}"
echo "Welcome Notebook created at ${WELCOME_NOTEBOOK_PATH}"

# Start Agent Backend
echo "Starting VectorBTPro Expert Agent Backend..."
# Change to agent_system directory to ensure Uvicorn finds the module correctly
# and any relative paths within agent_backend.py work as expected.
cd /home/jovyan/agent_system
# The Dockerfile should have already installed dependencies.
# PYTHONPATH is set in the Dockerfile or inherited, but explicitly adding /home/jovyan can help if needed.
# export PYTHONPATH=/home/jovyan:${PYTHONPATH} 
# Run Uvicorn as the jovyan user.
# Using `gosu` is not necessary here as we should already be the jovyan user or root,
# and Uvicorn itself doesn't require root if ports are > 1024.
# The Dockerfile should switch to jovyan user before this script is run if possible, or this script runs as root and uvicorn as jovyan.
# Given the Dockerfile structure, this script is run as root, so uvicorn is started as root.
# For better security, it's ideal if Uvicorn runs as non-root.
# However, the agent backend needs to write to /home/jovyan/work/knowledge_base, which jovyan owns.
# If this script is run as root, ensure the agent has write permissions or run it as jovyan.
# The `auto_initialize_agent` in agent_backend.py will use GEMINI_API_KEY from env.
echo "Current user for Uvicorn: $(whoami)"
echo "Launching Uvicorn..."
uvicorn agent_backend:app --host 0.0.0.0 --port 8000 &
AGENT_PID=$!
echo "Agent backend started with PID ${AGENT_PID}."
echo "Waiting a few seconds for agent backend to initialize..."
sleep 8 # Increased sleep for robust startup, SentenceTransformer model download etc.

# Check if agent backend started successfully (basic check)
if ps -p $AGENT_PID > /dev/null; then
   echo "Agent backend appears to be running."
else
   echo "ERROR: Agent backend (PID ${AGENT_PID}) does not appear to be running after startup!"
   echo "Please check the container logs for Uvicorn errors."
   # Consider exiting if agent is critical, or let Jupyter start and user can debug.
   # exit 1 
fi


# Start Jupyter Lab
echo "Starting Jupyter Lab..."
# JUPYTER_ENABLE_LAB=yes is often set in parent Docker images or by default.
# The start-notebook.sh script is the standard entrypoint for Jupyter Docker Stacks.
# It handles various initializations, including setting up user permissions and launching JupyterLab.
# We are running this script as root (common for entrypoints), start-notebook.sh will then
# use `gosu jovyan` to step down privileges for JupyterLab itself.
# The --ServerApp.notebook_dir should be /home/jovyan/work to give access to notebooks/, documentation/, etc.
# All files created by this script (notebook, startup script) are chowned to jovyan.
exec start-notebook.sh \
    --ServerApp.token='' \
    --ServerApp.password='' \
    --ServerApp.allow_root=False \
    --ServerApp.ip='0.0.0.0' \
    --ServerApp.port=8888 \
    --ServerApp.open_browser=False \
    --ServerApp.notebook_dir="/home/jovyan/work" \
    --ServerApp.terminado_settings='{"shell_command":["/bin/bash"]}'

# If exec fails, the script will exit due to set -e.
# The agent backend (AGENT_PID) will be terminated when the main process (JupyterLab) exits.
echo "Jupyter Lab process exited."
```
