# Dockerfile
# Basis-Image: Dein spezifiziertes Jupyter SciPy Notebook Image mit Python 3.11
FROM quay.io/jupyter/scipy-notebook:python-3.11

# Wechsel zum Root-Benutzer für Systeminstallationen und temporäre Dateien
USER root
WORKDIR /tmp

# Systemabhängigkeiten installieren:
# - cmake: Notwendig für den TA-Lib Build
# - curl, git: Für den Download von TA-Lib und Ollama Installer
# - ca-certificates: Für HTTPS-Verbindungen
# - software-properties-common: Für das Hinzufügen von Repositories (falls benötigt, aber hier nicht kritisch)
RUN apt-get update && \
    apt-get install -yq --no-install-recommends \
    cmake \
    curl \
    git \
    ca-certificates \
    software-properties-common && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# TA-Lib aus dem Quellcode kompilieren und installieren
# Dies ist eine Abhängigkeit für deine 'vectorbtpro' Installation
RUN wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar -xzf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4/ && \
    ./configure --prefix=/usr && \
    make && \
    make install && \
    rm -R /tmp/ta-lib-0.6.4 /tmp/ta-lib-0.6.4-src.tar.gz

# -----------------------------------------------------------
# Ollama Installation im Container
# Dies installiert den Ollama-Server und die CLI im Container.
# Die Modelle selbst werden später nach dem Start heruntergeladen.
ENV OLLAMA_HOME /root/.ollama
RUN curl -fsSL https://ollama.com/install.sh | sh

# -----------------------------------------------------------
# Wechsel zurück zum Standardbenutzer des Jupyter-Images ('jovyan')
USER ${NB_UID}

# 'uv' installieren (ein schneller Python-Paketmanager)
RUN pip install uv

# Kopiere deine Python-Projektdateien in das Container-Arbeitsverzeichnis
# Dies ist notwendig, damit 'uv' deine Projekt-Abhängigkeiten installieren kann
ADD ./vectorbtpro ./vectorbtpro
ADD pyproject.toml ./
ADD LICENSE ./
ADD README.md ./

# Installiere deine Projektabhängigkeiten und 'universal-portfolios'
# 'uv pip install --system' installiert Pakete in die Umgebung des Benutzers
RUN uv pip install --system --no-cache-dir ".[all]" && \
    uv pip install --system --no-cache-dir --no-deps 'universal-portfolios'

# -----------------------------------------------------------
# Installiere Jupyter AI und die Python-Client-Bibliotheken für die LLMs
# - jupyter-ai: Die Haupt-JupyterLab-Erweiterung für generative KI
# - ollama: Python-Client zur Interaktion mit dem Ollama-Server
# - gpt4all: Python-Client zum Laden und Nutzen von GPT4All-Modellen
# - huggingface_hub: Ermöglicht den Zugriff auf Modelle vom Hugging Face Hub
# - google-generativeai: Offizieller Python-Client für Google Gemini
# - openai: Optional, falls du auch OpenAI-Modelle nutzen möchtest
RUN pip install --no-cache-dir \
    jupyter-ai \
    ollama \
    gpt4all \
    google-generativeai 

# Aktiviere die JupyterLab Extension für Jupyter AI
# Notwendig, damit die UI-Komponenten von Jupyter AI in JupyterLab erscheinen
RUN jupyter labextension enable @jupyter-ai/jupyter-ai

# Das Problem mit Dash/Plotly beim Bauen beheben
# Manchmal notwendig nach der Installation von JupyterLab-Erweiterungen
RUN jupyter lab build --minimize=False

# -----------------------------------------------------------
# Optional: GPT4All Modell(e) herunterladen und ins Image integrieren (auskommentiert)
# Dies würde die Image-Größe stark erhöhen. Empfohlen ist der Download nach dem Start.
# ENV GPT4ALL_HOME /home/jovyan/.cache/gpt4all
# RUN mkdir -p ${GPT4ALL_HOME} && \
#     curl -L "https://gpt4all.io/models/gguf/mistral-7b-openorca.Q4_0.gguf" -o "${GPT4ALL_HOME}/mistral-7b-openorca.Q4_0.gguf"

# Exponiere die Ports für JupyterLab und Ollama
# Diese Ports sind für den Zugriff von deinem Host-PC auf die Dienste im Container
EXPOSE 8888
EXPOSE 11434

# Setze das Arbeitsverzeichnis auf das Standard-Work-Verzeichnis von JupyterLab
WORKDIR "$HOME/work"

# Startbefehl für den Container
# - 'ollama serve &': Startet den Ollama-Server im Hintergrund (als Daemon).
# - 'jupyter lab ...': Startet JupyterLab.
#   - '--ip=0.0.0.0': Erlaubt den Zugriff von jeder IP-Adresse (für Docker notwendig).
#   - '--port=8888': Setzt den Port, auf dem JupyterLab lauscht.
#   - '--no-browser': Verhindert, dass JupyterLab automatisch einen Browser auf dem Server öffnet.
#   - '--allow-root': Erlaubt JupyterLab, als Root zu laufen (falls der Benutzer im Container Root-Rechte hat, was in diesem Fall nicht der Fall ist, aber eine sichere Vorkehrung ist).
#   - '--ServerApp.token='': Deaktiviert die Token-Authentifizierung. Nur für Entwicklungsumgebungen empfohlen!
CMD ["bash", "-c", "ollama serve & jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.token=''"]