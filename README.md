# 🗂️ Universal File Server

A powerful, web-based file server that allows you to browse and stream files from your computer to any device on the same network. Built with Python and Flask using the MVC pattern.

## ✨ Features

- 🌐 Web Interface: Access your files from any device with a web browser
- 🎮 Keyboard Shortcuts: Full keyboard navigation support
- 📱 Mobile Friendly: Responsive design works on phones and tablets
- 🎬 Media Streaming: Stream videos with seek support
- 🔍 File Search: Search across entire drives
- 📊 File Type Detection: Smart icons and organization
- 🚀 No External Dependencies: Uses only Python standard libraries

## 🎯 Keyboard Shortcuts

| Key | Action |
|-----|--------|e
| `↑` `↓` | Navigate between files |
| `Enter` | Open selected item |
| `Backspace` | Go to parent directory |
| `/` | Focus search box |
| `Escape` | Clear selection |

## 🚀 Quick Start

### Prerequisites

- Python 3.7 or higher
- Flask library

### Installation

1. Clone or download the project files:
   ```bash
   git clone <repository-url>
   cd universal_file_server

2. Setup Virtual Environment
    ```bash
    python3 setup_project.py
    source env/bin/activate
    pip install -r requirements.txt

3. Run Server
    ```bash
    python app.py