# User Guide

## Getting Started

### Registration & Login

1. Open the app in your browser
2. Click "Register" to create a new account
3. Enter a username, password (min 8 chars), and optional email
4. Log in with your credentials

### Forgot Password

1. On the login page, click "Forgot Password?"
2. Enter your email address
3. If the email exists, a reset link is sent
4. If the email doesn't exist, you're redirected to registration

## Chat Interface

### Sending Messages

- Type your message in the input box at the bottom
- **Enter** — new line
- **Ctrl+Enter** — send message
- Press the send button to send

### Message Actions

Each message has action buttons on hover:

| Button | Action |
|---|---|
| Edit (pencil) | Edit your message, AI re-responds |
| Regenerate | AI generates a new response |
| Fork | Create a branch from this message |
| Copy | Copy message content |
| Export (↓) | Download message as markdown |
| Toggle Markdown (`</>`) | Switch between rendered and plain text |

### Streaming

During AI generation:
- Tokens appear word-by-word
- TPS (tokens per second) is shown in real-time
- Total token count updates live
- Click "Stop" to cancel generation

## Session Management

### History Sidebar

- All your sessions are listed on the left
- Pinned sessions appear at the top
- Search sessions by title using the search bar
- Click any session to load it

### Session Actions

- **Pin** — Click the pin icon to pin/unpin
- **Archive** — Click the archive icon to archive/unarchive
- **Rename** — Double-click the session title to rename
- **Delete** — Click the trash icon to delete (with confirmation)

### Branch Tree

Click the branch icon (![branch]) in the header to open the branch tree panel. It shows:
- The current session
- Its parent session (if forked)
- Child branches (if any)
- Click any branch to navigate to it

### Session Search

Press **Ctrl+F** within a session to open the search overlay. Type to filter messages. Press Enter to jump between matches.

## Settings

### Opening Settings

Click the gear icon (![gear]) in the header or go to `/settings`.

### Available Settings

| Section | Settings |
|---|---|
| System Prompt | Customize the AI's behavior (supports `{date}`, `{time}`, `{datetime}`, `{user}`) |
| AI Model | Choose your default model |
| Temperature | Control response randomness (0.0–2.0) |
| AI Providers | Select provider, enter API key, configure Ollama URL |
| Tools | Add custom function-calling tools |
| Templates | Load a preset system prompt template |
| Accent Color | Customize the UI accent color |
| Font Size | Adjust text size |
| Theme | Dark/Light (also toggled via header button) |
| Export | Download current chat as Markdown/JSON/HTML |
| Database | Backup/Restore SQLite database |
| System Health | Check if Ollama is running |
| Danger Zone | Delete your account permanently |

## Projects (RAG)

### Creating a Project

1. Click "+ New Project" in the sidebar
2. Enter a project name
3. Upload files (PDFs, code files, markdown notes)
4. Click Create

### Using a Project

- Select the project from the sidebar
- Start chatting — the AI reads all uploaded files as context
- The project name appears in the chat header

## Prompt Library

1. Click the Library button in the sidebar
2. Click "Add Prompt" to save a frequently used system prompt
3. Click any saved prompt to apply it to the current session

## Profile

Access your profile from the header (shows your initials/avatar).

In your profile you can:
- Change your username, email, or full name
- Upload a profile picture
- Change your password
- View usage statistics
- View archived sessions

## Admin Features

If you're an admin user, an "Admin" button appears in the header.

### Admin Panel (`/admin`)
- View all registered users
- Navigate to the Admin Dashboard

### Admin Dashboard (`/admin_dashboard`)
- **User Management** — View all users, click any user for details
- **Global Provider** — Set default provider and model for all users
- **Global System Prompt** — Default system prompt
- **Registration Toggle** — Enable/disable registration
- **Global Tools** — Add function-calling tools available to all users

### User Detail View (`/admin/user/<uid>`)
Click any user in the dashboard to see:
- User profile info and avatar
- Usage statistics (sessions, messages, tokens)
- All chat sessions with details
- Admin actions:
  - Change user role (user/admin)
  - Reset user password
  - Block/unblock user
  - Delete user (with confirmation)
