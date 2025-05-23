# Base image
FROM jupyter/scipy-notebook:python-3.9.18

# Switch to root user for system-level installations
USER root

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    cmake \
    curl \
    unzip \
    # Clean up apt cache
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Install TA-Lib from source
RUN curl -L http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz -o ta-lib-0.4.0-src.tar.gz && \
    tar -xzf ta-lib-0.4.0-src.tar.gz && \
    cd ta-lib/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    cd .. && \
    rm -rf ta-lib ta-lib-0.4.0-src.tar.gz

# Install Jupyter extensions and Python dependencies for vectorbtpro
# Using --no-cache-dir to keep image size down
RUN pip install --no-cache-dir \
    jupyter-dash \
    plotly \
    kaleido \
    jupyter-server-proxy \
    ipywidgets \
    jupyterlab-widgets

# Install Python dependencies for vectorbtpro (pinned versions)
RUN pip install --no-cache-dir \
    numpy==1.23.5 \
    numba==0.57.1 \
    pandas==1.5.3 \
    scipy==1.10.1 \
    matplotlib==3.7.1 \
    plotly==5.15.0 \
    ipython==8.12.2 \
    ipykernel==6.23.1 \
    ipywidgets==8.0.6 \
    requests==2.31.0 \
    sqlalchemy==2.0.15 \
    pytz==2023.3 \
    pandas-datareader==0.10.0 \
    yfinance==0.2.28 \
    ccxt==3.0.80 \
    quantstats==0.0.62 \
    schedule==1.2.0 \
    scikit-learn==1.2.2 \
    statsmodels==0.14.0 \
    pyarrow==12.0.1 \
    TA-Lib==0.4.28 \
    # Other common data science packages that might be useful
    seaborn \
    patsy

# Install Python dependencies for the AI Agent
RUN pip install --no-cache-dir \
    fastapi \
    "uvicorn[standard]" \
    google-generativeai>=0.3.0 \
    chromadb \
    sentence-transformers \
    langchain \
    langchain-google-genai \
    markdown \
    beautifulsoup4 \
    aiofiles \
    websockets \
    python-multipart

# Install Jupyter AI and magics
RUN pip install --no-cache-dir jupyter-ai jupyter-ai-magics

# Copy vectorbtpro source, pyproject.toml, LICENSE, README.md
# These files are expected to be in the build context
COPY --chown=${NB_UID}:${NB_GID} vectorbtpro/ /home/jovyan/vectorbtpro/
COPY --chown=${NB_UID}:${NB_GID} pyproject.toml /home/jovyan/pyproject.toml
COPY --chown=${NB_UID}:${NB_GID} LICENSE /home/jovyan/LICENSE
COPY --chown=${NB_UID}:${NB_GID} README.md /home/jovyan/README.md

# Switch to jovyan user to install vectorbtpro
USER ${NB_UID}
WORKDIR /home/jovyan

# Install vectorbtpro
RUN pip install --no-cache-dir .

# Copy agent system code
COPY --chown=${NB_UID}:${NB_GID} agent_system/ /home/jovyan/agent_system/

# Switch back to root to copy start.sh and set permissions
USER root

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

# Create working directories and set permissions
RUN mkdir -p /home/jovyan/work/documentation \
             /home/jovyan/work/knowledge_base \
             /home/jovyan/work/notebooks \
             /home/jovyan/work/data && \
    chown -R ${NB_UID}:${NB_GID} /home/jovyan/work

# Switch to jovyan user for subsequent commands
USER ${NB_UID}

# Set default working directory
WORKDIR /home/jovyan/work

# Build JupyterLab to include extensions
# This can be slow, so it's placed after most pip installs
# but before it's actually needed.
RUN jupyter lab build

# Expose ports for Jupyter and the Agent API
EXPOSE 8888
EXPOSE 8000

# Set the entry point
CMD ["start.sh"]
