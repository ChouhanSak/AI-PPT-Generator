# AI PPT Generator

An AI-powered presentation generation system designed to create structured, context-aware, and visually planned PowerPoint presentations from a simple topic.

Unlike basic AI presentation generators that directly convert a prompt into generic slides, this project uses a multi-stage AI intelligence pipeline. Each stage performs a specialized presentation task such as topic analysis, storyline planning, quality evaluation, and revision before slide content and visual design are generated.

> This project is currently under active development.

---

## Project Goal

The goal of this project is to build a specialized AI system focused on presentation creation.

The system is designed to:

- Understand the actual meaning and domain of a presentation topic.
- Identify the concepts that must be covered.
- Build a logical narrative across slides.
- Maintain the exact slide count requested by the user.
- Detect generic, repetitive, or technically weak presentation content.
- Revise low-quality storylines before slide generation.
- Generate concise slide-worthy content.
- Plan visual direction and slide layouts.
- Produce editable `.pptx` presentations.

---

## Current AI Architecture

The presentation intelligence system is being developed as a multi-stage pipeline.

```text
Presentation Topic
        |
        v
+----------------------+
|    Topic Analyzer    |
+----------------------+
        |
        v
+----------------------+
|  Storyline Planner   |
+----------------------+
        |
        v
+----------------------+
|      PPT Critic      |
+----------------------+
        |
        +---- APPROVE ----> Accepted Storyline
        |
        +---- REVISE -----> Storyline Reviser
        |                         |
        |                         v
        |                    PPT Critic
        |
        +---- REJECT ------> Fresh Storyline
```

Future pipeline stages:

```text
Accepted Storyline
        |
        v
+----------------------+
|     Slide Writer     |
+----------------------+
        |
        v
+----------------------+
|   Visual Director    |
+----------------------+
        |
        v
+----------------------+
|  PowerPoint Builder  |
+----------------------+
        |
        v
Editable .pptx File
```

---

## AI Engine Components

### Topic Analyzer

The Topic Analyzer studies the presentation request before any slides are created.

It identifies:

- Topic domain
- Presentation type
- Presentation goal
- Audience depth
- Central question
- Core concepts
- Recommended conceptual progression
- Possible topic drift
- Content accuracy risks

The analyzer does not generate slides or presentation bullets.

---

### Storyline Planner

The Storyline Planner converts the topic analysis into a connected presentation narrative.

Each slide receives:

- Slide number
- Narrative role
- Slide purpose
- Core message
- Concepts used
- Transition to the next slide

The planner is required to generate exactly the number of slides requested by the user.

---

### PPT Critic

The PPT Critic evaluates the generated storyline before it is accepted.

It checks:

- Topic relevance
- Narrative flow
- Content specificity
- Technical care
- Audience fit
- Generic presentation language
- Unsupported claims
- Repetitive slide functions
- Topic drift

The critic returns a quality score and one of three decisions:

```text
APPROVE
REVISE
REJECT
```

---

### Storyline Reviser

The Storyline Reviser improves storylines based on structured critic feedback.

It can correct:

- Technically overconfident claims
- Unsupported absolute statements
- Generic AI-generated language
- Audience mismatch
- Narrative gaps
- Topic drift
- Repetitive slide functions

The reviser preserves the requested slide count and performs targeted revisions instead of rebuilding the entire presentation unnecessarily.

---

### Gemini Client

The Gemini client is a centralized AI API layer being developed to manage model requests.

Its responsibilities include:

- Centralized model configuration
- API request handling
- Temporary error detection
- Retry handling
- Rate-limit classification
- Daily quota detection
- Clear AI service errors

The client distinguishes temporary API failures from exhausted daily quotas so the system does not perform unnecessary retries.

---

### Slide Writer

Currently under development.

The Slide Writer will transform an accepted storyline into concise presentation content.

The goal is to avoid paragraph-heavy and generic AI-generated slides.

---

### Visual Director

Currently under development.

The Visual Director will determine the visual strategy of the presentation, including:

- Slide composition
- Information hierarchy
- Layout selection
- Visual density
- Diagram opportunities
- Data visualization opportunities
- Presentation pacing

---

## Project Structure

```text
ai-ppt-generator/
|
|-- ai_engine/
|   |-- __init__.py
|   |-- gemini_client.py
|   |-- pipeline.py
|   |-- topic_analyzer.py
|   |-- storyline_planner.py
|   |-- storyline_reviser.py
|   |-- ppt_critic.py
|   |-- slide_writer.py
|   `-- visual_director.py
|
|-- static/
|   |-- script.js
|   `-- style.css
|
|-- templates/
|   `-- index.html
|
|-- app.py
|-- ppt_generator.py
|-- requirements.txt
|-- README.md
`-- .env
```

The `.env` file is used locally for environment variables and API credentials and must not be committed to version control.

---

## Tech Stack

### Backend

- Python
- Flask
- Flask-CORS

### AI Integration

- Gemini API
- Google Gen AI Python SDK

### Presentation Generation

- python-pptx

### Frontend

- HTML
- CSS
- JavaScript

### Environment Management

- python-dotenv
- Python virtual environment

---

## Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-ppt-generator
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
```

Activate the environment.

Windows:

```bash
venv\Scripts\activate
```

macOS/Linux:

```bash
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root.

```env
GEMINI_API_KEY=your_api_key_here
```

Never commit the `.env` file or real API credentials to version control.

### 5. Run the Application

```bash
python app.py
```

The local development server will start on:

```text
http://127.0.0.1:5000
```

---

## Current Development Status

Completed:

- Topic analysis engine
- Structured topic understanding
- Storyline planning
- Exact slide count enforcement
- Presentation quality critic
- Storyline revision engine
- Multi-stage storyline quality pipeline
- Initial centralized Gemini client
- Temporary API error handling
- Daily quota detection

In Progress:

- Centralizing all AI requests through the Gemini client
- Development fixtures for API-free testing
- Slide Writer
- Visual Director
- Presentation quality dataset collection

Planned:

- Automated slide content generation
- Visual direction engine
- Additional slide layouts
- Diagrams and visual storytelling
- Dataset generation from reviewed presentation outputs
- Specialized presentation model experimentation
- End-to-end presentation quality evaluation
- Editable PowerPoint generation through the complete AI pipeline

---

## Design Philosophy

The system follows one core principle:

> A good presentation is not a collection of independent slides. It is a structured narrative where every slide performs a specific intellectual and visual function.

The project therefore separates topic understanding, narrative planning, quality evaluation, revision, slide writing, and visual direction into specialized components.

---

## Security

Sensitive credentials must never be committed to the repository.

The following files and directories should remain excluded from version control:

```text
.env
venv/
__pycache__/
*.pyc
*.pptx
```

API keys should always be loaded through environment variables.

---

## Development Note

The current AI pipeline uses the Gemini API as a teacher and generation layer while the presentation intelligence architecture, evaluation pipeline, and future training dataset are being developed.

The long-term research direction is to experiment with a specialized presentation-focused model using curated high-quality presentation planning and critique data.

---

## Author

**Sakshi Chouhan**

---

## License

This project is currently intended for educational, development, and experimentation purposes.