# Perfume Store with a Local AI Assistant

A bilingual (English and Arabic) educational perfume e-commerce website built with Django. Visitors can browse the catalog and ask the store assistant about products. The assistant uses the store's own data for catalog questions and can use local large language models for general questions, without sending prompts to a cloud AI service.

> **Offline use:** Docker images and both AI models must be downloaded once while connected to the internet. After setup, the site and assistant can run locally without internet as long as Docker Desktop is running and the Docker images, Ollama models, and project data have not been removed.

## Contents

- [Features](#features)
- [Technology](#technology)
- [How the Docker and local AI setup was built](#how-the-docker-and-local-ai-setup-was-built)
- [Prerequisites](#prerequisites)
- [One-command setup on another computer](#one-command-setup-on-another-computer)
- [First-time setup](#first-time-setup-internet-required)
- [Run offline](#run-the-project-offline)
- [Try the assistant](#try-the-assistant)
- [Project configuration](#project-configuration)
- [API endpoints](#api-endpoints)
- [Run Django without Docker](#run-django-without-docker)
- [Troubleshooting](#troubleshooting)
- [Limitations and privacy](#limitations-and-privacy)

## Features

- Perfume catalog and store pages with English and Arabic content.
- Shopping cart and sample order workflow; this educational project does not process real payments.
- Store dashboard for managing products, orders, and website content.
- Store assistant that answers product and price questions using the current store data.
- Local Ollama integration for general questions, Arabic and English conversation, and calculations.
- Two selectable local models: `qwen3:4b` and `hermes3:3b`.
- Docker Compose setup for the Django website and the local AI service.

## Technology

- **Website and API:** Python, Django, Django REST Framework, HTML templates, CSS, and JavaScript.
- **Containerization:** Docker and Docker Compose.
- **Local inference server:** Ollama.
- **Language models:** Qwen 3 4B and Hermes 3 3B, served locally by Ollama.
- **Database:** SQLite for this educational project.

## How the Docker and local AI setup was built

The Docker setup packages the web application and runs Ollama as a separate local service. Docker Compose connects the services on a private network, so Django sends assistant requests to Ollama at `http://ollama:11434` inside Docker. The Ollama port is published only on the local computer (`127.0.0.1:11434`).

The setup consists of:

1. **`Dockerfile`** starts from Python 3.12, installs the packages listed in `requirements.txt`, copies the Django source into the image, and starts Django after applying database migrations.
2. **`compose.yaml`** defines three services:
   - `web`: builds and runs the Django site on port `8000`.
   - `ollama`: runs the local Ollama server and keeps downloaded model files in the `ollama_data` volume.
   - `ollama-models`: waits for Ollama, checks whether each required model is already available, and downloads it only when it is missing. It must finish before the web service starts.
3. **Persistent data:** Ollama models are stored in a named Docker volume. The existing SQLite database and media directory are mounted from the project folder.
4. **Django assistant integration:** the assistant service answers store-related questions from the local catalog and calls Ollama for general prompts. Simple arithmetic is handled locally for reliable results. The assistant follows the language of the question where possible.
5. **Model selection:** the assistant interface lets the user choose Qwen 3 4B (the default) or Hermes 3 3B. Both are stored in the persistent Ollama volume.

The main project files for this setup are `Dockerfile`, `compose.yaml`, `config/settings.py`, `store/api.py`, `store/assistant_service.py`, `store/assistant_ml.py`, and `store/templates/base.html`.

## Prerequisites

- A computer with Docker Desktop installed (macOS, Windows, or Linux with Docker Engine and the Compose plugin).
- Docker Desktop / Docker Engine running.
- About 5 GB of free space for both model files, in addition to Docker images and application data. Actual storage use varies by platform and image version.
- Internet access for the initial image and model downloads only.

## One-command setup on another computer

Copy or extract the **entire project folder** to the other computer. Keep `compose.yaml`, `Dockerfile`, the Django source folders, `db.sqlite3`, and `media/` together. The Ollama models are stored in a Docker volume and are not included in the project folder, so the new computer downloads them during its first setup.

Install Docker Desktop first and start it. Installing Docker itself is an operating-system-level step and is deliberately not automated by these project scripts; it may require administrator approval and differs between macOS, Windows, and Linux. The setup scripts then build the web image, start Ollama, download any missing models, start the website, list the models, and open the site. Internet access is required the first time, and both model downloads can take a while.

- **macOS/Linux:** from Terminal, open the project folder and run `./setup.sh`. If macOS reports that the script is not executable, run `chmod +x setup.sh` once, then run `./setup.sh`.
- **Windows:** open PowerShell in the project folder and run `powershell -ExecutionPolicy Bypass -File .\setup.ps1`.

When setup completes, the store opens at <http://localhost:8000/en/>. On later runs, start Docker Desktop and run the same script again; Compose reuses the already downloaded images and models. To stop the project while keeping data, run `docker compose down` from the project folder. Do not run `docker compose down --volumes` if you want to keep the downloaded models.

This is reproducible local setup using Infrastructure as Code: `compose.yaml` declares the services and their connections, while the scripts automate the setup steps. The project folder must still be copied to each computer, and the first setup on each computer needs internet to download its Docker images and Ollama models.

## First-time setup (internet required)

Open a terminal in the project directory and build and start the services:

```bash
docker compose up --build -d
```

The first run builds the web image and downloads the Ollama image, `hermes3:3b`, and `qwen3:4b`. Model downloads can take several minutes. Check startup progress with:

```bash
docker compose ps
docker compose logs -f ollama-models
```

When model setup has completed, open the website:

- Store: <http://localhost:8000/en/>
- Arabic store: <http://localhost:8000/ar/>
- Local Ollama endpoint: <http://localhost:11434>

The model setup service exits successfully after checking/downloading the models; that is expected. The `web` and `ollama` services should remain running.

## Run the project offline

After completing first-time setup, the following steps work without an internet connection:

1. Start Docker Desktop and wait until its engine is running.
2. Open Terminal.
3. Change to the project directory. For the usual Desktop location, run:

   ```bash
   cd ~/Desktop/perfume-project
   ```

4. Start the containers:

   ```bash
   docker compose up -d
   ```

5. Wait for the services to start, then open <http://localhost:8000/en/>.
6. Open the assistant on the page and ask a question in Arabic or English.
7. When finished, stop the containers while keeping models and data:

   ```bash
   docker compose down
   ```

The Compose configuration checks for each model locally and skips its download when it is already present. Do not use `docker compose down --volumes` if you want to keep the downloaded models and Docker-managed data.

## Try the assistant

Example prompts:

- `What perfumes are available?`
- Ask for available perfumes in Arabic.
- `How much does [a product] cost?`
- `What is 17 × 24?`
- `Explain photosynthesis in simple words.`
- Ask the assistant a simple question in Arabic.

Use the assistant's model selector to switch between `Qwen 3 4B` and `Hermes 3 3B`. They are separate models and may differ in speed and response quality on this hardware; compare them with the same prompts before choosing one for a presentation. Local language models can still make mistakes, especially on specialized factual questions, so verify important information.

## Project configuration

The Compose file sets these environment variables for the web service:

| Variable | Purpose | Compose default |
| --- | --- | --- |
| `DJANGO_DEBUG` | Enables Django debug mode for local development. | `1` |
| `DJANGO_ALLOWED_HOSTS` | Hostnames accepted by Django. | `localhost,127.0.0.1,web` |
| `OLLAMA_BASE_URL` | Address of the Ollama service from inside Docker. | `http://ollama:11434` |
| `OLLAMA_MODEL` | Default model for assistant requests. | `qwen3:4b` |
| `OLLAMA_REQUEST_TIMEOUT_SECONDS` | Maximum wait for a local model response before the assistant falls back to its unavailable message. | `120` |
| `DJANGO_DATABASE_PATH` | SQLite database file path inside the container. | `/data/db.sqlite3` |

These defaults are intended for local coursework and demonstration, not for deploying a public production website. Configure production security settings before exposing the application to the internet.

## Use with VS Code

Open the `perfume-project` folder in VS Code. The workspace `.vscode/settings.json` enables BYOK models in the current chat agent host and points the official Ollama extension at the local Ollama endpoint. After opening the folder, reload the VS Code window if prompted, start the Docker services as described above, and confirm both configured models are listed:

```bash
docker compose exec ollama ollama list
```

Open the Chat view, start a new chat, choose `qwen3:4b` or `hermes3:3b`, and use **Ask** for ordinary questions. If the picker is stale, run **Ollama: Refresh Models** from the Command Palette, then select the Ollama provider. A model appearing in the picker confirms discovery only; verify that the prompt receives a visible response. On 2026-10-19, both models appeared in the refreshed picker, but a Hermes arithmetic prompt remained pending for about 90 seconds and was cancelled without a visible answer. Successful VS Code Chat replies therefore remain unverified. On this computer (MacBook Air M1, 8 GB RAM; Docker memory limit about 3.73 GB), general Arabic model generation also timed out after 120 seconds in the website-backed Ollama request. Direct CLI smoke checks for both models did return `100` for `10 × 10`, but Qwen 3 4B was observed to be substantially slower than Hermes during the test. Treat these as limited smoke checks, not evidence of reliable general-chat performance. The website's local arithmetic path returned the correct answer in both Arabic and English without invoking an LLM. See [docs/architecture.md](docs/architecture.md) and [research/methodology_and_results.md](research/methodology_and_results.md) for architecture and detailed current-device checks.

VS Code chat through a local Ollama model can work offline after the extension, VS Code, Docker image, and model files are already installed. Copilot features that depend on GitHub services (including some semantic search, embeddings, and inline code completion) still need connectivity and are not part of the local model path. To use the store's exact assistant routing from a VS Code terminal, call the local Django API at `http://127.0.0.1:8000/api/assistant/`; the Chat view talks directly to the selected Ollama model and does not run the website's intent or catalogue logic.

For direct Django work, select the existing `venv/bin/python` interpreter on macOS/Linux or `venv\Scripts\python.exe` on Windows; a fresh checkout can create the virtual environment using the commands in **Run Django without Docker**. The integrated terminal can run the Docker Compose commands in this guide.

## API endpoints

- `GET /api/products/`: list available products; authenticated administrators can create, update, or delete products.
- `/api/orders/`: administrator access to orders and order status.
- `/api/site-content/`: read homepage content; updates require an administrator.
- `POST /api/assistant/`: submit a question to the store assistant in Arabic or English.
- `/api/`: browsable API index. `/api-auth/login/` provides the Django REST Framework browser login.

Dashboard changes require an administrator account. Create one inside the running web container with:

```bash
docker compose exec web python manage.py createsuperuser
```

Then sign in to the store dashboard at <http://localhost:8000/dashboard/>.

## Run Django without Docker

Docker is the recommended way to run the complete website and local AI assistant together. To run only Django directly on the computer, create and activate a Python virtual environment, install dependencies, apply migrations, and start the development server:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

On Windows PowerShell, activate the environment with `venv\Scripts\Activate.ps1`. To use the Ollama-backed assistant in this mode, install and run Ollama separately, download one of the model names above, and configure the application to reach the local Ollama server.

## Troubleshooting

- **The site does not open:** confirm Docker Desktop is running, then inspect services with `docker compose ps` and web logs with `docker compose logs -f web`.
- **The assistant says the local AI is unavailable:** check `docker compose ps` and `docker compose logs -f ollama`. Wait for Ollama's health check to pass, then retry.
- **Model setup is still running:** inspect `docker compose logs -f ollama-models`. The first download can take a while. Internet is needed if a required model is missing.
- **Port 8000 is already in use:** stop the other local service using that port, or change the host side of the `web` port mapping in `compose.yaml`.
- **Need to stop and start again:** use `docker compose down` and then `docker compose up -d`. This keeps the named Ollama volume and project files.
- **Need a clean reset:** `docker compose down --volumes` deletes the named Ollama model volume. Models must be downloaded again. Use this only if you intend to reset Docker-managed data.

## Limitations and privacy

- The AI models run locally through Ollama; assistant prompts are not sent to a hosted AI API by this configuration.
- The model setup needs internet only if Docker images or model files are not already available locally. No new facts from the internet are available during offline use.
- A small local model may produce incomplete or inaccurate general answers. Verify important answers independently.
- Store contact details are deliberately shown as unconfigured demo content; add the store’s verified contact information before presenting the site publicly.
- The site is an educational project. Its sample checkout does not collect payments and its development Docker configuration is not hardened for public production use.
