<div align="center">

<img src="static/images/logo.svg" alt="LocalNeural Logo" width="120" height="120" />

# LocalNeural

**The Ultimate Private AI Interface. Local. Fast. Beautiful.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![Ollama](https://img.shields.io/badge/Powered%20By-Ollama-white.svg)](https://ollama.com/)

[**Explore the Code**](https://github.com/rkstudio585/LocalNeural) · [**Report Bug**](https://github.com/rkstudio585/LocalNeural/issues) · [**Request Feature**](https://github.com/rkstudio585/LocalNeural)

</div>

---

## 🌟 Introduction

Welcome to **LocalNeural**, a cutting-edge, self-hosted web interface designed to interact with your local LLMs (Large Language Models) via **Ollama**.

In a world where data privacy is paramount, LocalNeural bridges the gap between powerful AI and complete data sovereignty. It features a stunning **"Nothing OS" inspired UI** mixed with **Liquid Glassmorphism**, offering a premium user experience comparable to top-tier commercial AI platforms—but running entirely on your machine.

Whether you are a developer needing a coding assistant, a writer brainstorming ideas, or a researcher organizing documents, LocalNeural provides the tools you need with zero latency and zero data tracking.

---

## ✨ Key Features

*   **⚡ Real-Time Streaming:** Experience word-by-word streaming responses via WebSockets, just like ChatGPT.
*   **🧠 Context-Aware Memory:** The AI remembers your conversation history, allowing for deep, multi-turn discussions.
*   **📂 Project Workspaces (RAG):** Create isolated projects and upload **PDFs, Code files, and Markdown notes**. The AI will read your files and use them as knowledge to answer your questions.
*   **🎨 Stunning UI/UX:** A dark-themed, dot-matrix background with frosted glass elements and smooth Material 3 animations.
*   **📸 Multimodal Support:** Drag and drop images or paste them from your clipboard to have the AI analyze them (requires vision models like `llava`).
*   **📝 Markdown & Code Highlighting:** Beautiful rendering of mathematical formulas, tables, and syntax-highlighted code blocks with one-click copying.
*   **🔄 Regenerate & Edit:** Made a mistake? Edit your prompt or ask the AI to try again with a single click.
*   **💾 Prompt Library:** Save your favorite system prompts and inject them into any chat instantly.
*   **📥 Export Options:** Download your conversations as Markdown, JSON, or HTML/PDF.

---

## 🛠️ Prerequisites

Before you begin, ensure you have the following installed on your system:

1.  **Python 3.8+**: The backend engine.
2.  **Ollama**: The core AI runner. [Download here](https://ollama.com).
    *   *Note:* Ensure you have pulled a model (e.g., `ollama pull llama3`) and the service is running (`ollama serve`).

---

## 🚀 Installation & Setup

Follow these simple steps to get LocalNeural running on your machine.

### 1. Clone the Repository
  ```bash
  git clone https://github.com/rkstudio585/LocalNeural.git
  cd LocalNeural
  ```
  
### 2. Set Up Virtual Environment (Optional but Recommended)
  ```bash
  python -m venv venv
  # Windows
  venv\Scripts\activate
  # Mac/Linux
  source venv/bin/activate
  ```

### 3. Install Dependencies
  ```bash
  pip install -r requirements.txt
  ```
  *(Dependencies include: `flask`, `flask-socketio`, `requests`, `eventlet`, `pypdf`)*

### 4. Run the Application
  ```bash
  python app.py
  ```

### 5. Access the Interface
Open your browser and navigate to: `http://localhost:5000`

---

## 🧠 How It Works

LocalNeural uses a **Model-View-Controller (MVC)** architecture powered by **ollama**, **Flask** and **WebSockets**.

### The Architecture
1.  **Frontend (View):** Built with HTML5, TailwindCSS, and jQuery. It handles user inputs, file drops, and renders the Markdown response. It connects to the backend via `Socket.IO` for bidirectional, low-latency communication.
2.  **Backend (Controller):** `app.py` acts as the brain. It receives prompts, queries the SQLite database for context, and forwards the request to the running Ollama instance.
3.  **Database (Model):** A robust `SQLite` database stores:
    *   `sessions`: Chat metadata and settings.
    *   `messages`: The actual conversation history.
    *   `projects` & `documents`: Uploaded files for the Knowledge Base.
4.  **AI Engine:** Ollama runs locally, processing the prompt and streaming tokens back to Flask, which instantly pushes them to your browser.

### Context Injection (Project Mode)
When you create a **Project** and upload files:
1.  The backend parses the text from PDFs or Code files.
2.  This text is stored in the database linked to the Project ID.
3.  When you chat inside that project, the system silently injects the file contents into the **System Prompt** of the AI.
4.  This allows the AI to "read" your files and answer specific questions about them.

---

## 📖 How To Use

### 1. Starting a Chat
Simply type in the input box and hit **Ctrl+Enter**. 
*   **Enter:** Creates a new line.

### 2. Managing Projects (Knowledge Base)
1.  Click **"+ New Project"** in the sidebar.
2.  Give it a name (e.g., "Python Learning").
3.  Upload relevant PDF text books or Python scripts.
4.  Click Create. The AI now knows everything inside those files for this specific chat session.

### 3. Using Images
*   **Drag & Drop** an image onto the text area.
*   **Paste** an image directly from your clipboard (`Ctrl+V`).
*   Ask the AI: *"What is in this image?"* (Ensure you have a vision-capable model selected).

### 4. Prompt Library
1.  Click the **Library** button in the sidebar.
2.  Add frequently used prompts (e.g., "Act as a Senior React Developer").
3.  Click any saved prompt to instantly insert it into your input box.

---

## 📂 Project Structure

  ```text
  LocalNeural/
  ├── app.py                 # Main application entry point (Server)
  ├── config.py              # Configuration settings
  ├── database.py            # SQLite database management logic
  ├── requirements.txt       # Python dependencies
  ├── README.md              # Project overview
  ├── LICENSE                # Project MIT License
  ├── .data/
  │   └── neural_memory.db   # SQL neural memory
  ├── utilities/
  │   ├── chat_logic.py      # AI Title generation & context helpers
  │   └── file_parser.py     # Extract text from PDFs/Code files
  ├── static/
  │   ├── css/
  │   │   └── style.css      # Custom styling & animations
  │   ├── images
  │   │   └── logo.svg       # Project SVG logo
  │   └── js/
  │       ├── main.js        # Core frontend logic & sockets
  │       └── chat_extras.js # UI helpers (Regenerate, Copy, etc.)
  └── templates/
      ├── base.html          # Main HTML layout
      ├── index.html         # Chat interface
      └── settings.html      # Configuration modal
  ```

---

## 🤝 Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  **Fork** the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a **Pull Request**.

Have a bug report or a feature request? Please [open an issue](https://github.com/rkstudio585/LocalNeural/issues)!

---

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.

---

<div align="center">

Made with ❤️ by  [rkriad585](https://github.com/rkriad585)

</div>
