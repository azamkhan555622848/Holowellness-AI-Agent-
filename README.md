# HellWellness Chatbot UI

This project is a frontend interface for a chatbot, designed to provide a seamless and interactive user experience. It allows users to send messages to a backend chatbot service and receive responses, with a clean and modern UI.

## Features

*   **Interactive Chat Interface:** Send and receive messages in a familiar chat format.
*   **Real-time "Thinking" Indicator:** Provides visual feedback to the user while the bot is processing a request.
*   **Session Management:** Remembers the user's session across interactions using `localStorage`.
*   **Conversation Clearing:** Allows users to clear the current chat history and reset the session with the backend.
*   **User-Friendly Design:** Includes components like `ChatHeader`, `ChatMessage`, and `ChatInput` for a structured and intuitive experience.

## Tech Stack

*   **React:** A JavaScript library for building user interfaces.
*   **TypeScript:** A typed superset of JavaScript that compiles to plain JavaScript, enhancing code quality and maintainability.
*   **Next.js (Implicit):** While not explicitly stated in the provided `ChatBot.tsx`, the project structure and typical React development often involve Next.js or Create React App. This README assumes a common React setup. If using Next.js, features like routing and API routes might be utilized.
*   **Tailwind CSS (Likely):** Based on the use of `className` attributes with utility-style classes (e.g., `fixed bottom-4 right-4`), it's highly probable that Tailwind CSS is used for styling.
*   **Vite:** A fast build tool and development server.

## Project Structure

A brief overview of the key components:

```
src/
├── components/
│   ├── chat/
│   │   ├── ChatBot.tsx       # Main chatbot component, orchestrates chat functionality
│   │   ├── ChatHeader.tsx    # Header component for the chat window
│   │   ├── ChatInput.tsx     # Input field for users to type messages
│   │   └── ChatMessage.tsx   # Component to display individual chat messages
│   └── ThinkingBar.tsx     # Visual indicator for when the bot is processing
└── ... (other potential files and folders like pages, styles, utils)
```

## Getting Started

### Prerequisites

*   Node.js (v18.x or later recommended)
*   npm (usually comes with Node.js) or yarn

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/azamkhan555622848/HellWellness-Chatbot-UI.git
    ```
2.  **Navigate to the project directory:**
    ```bash
    cd HellWellness-Chatbot-UI
    ```
3.  **Install dependencies:**
    ```bash
    npm install
    # or
    # yarn install
    ```

### Running the Development Server

```bash
npm run dev
# or
# yarn dev
```
This will typically start the development server (e.g., on `http://localhost:5173` if using Vite, or `http://localhost:3000` for Next.js).

## Configuration

The chatbot currently communicates with a backend API endpoint:
- `[YOUR_BACKEND_URL]/api/chat` for sending messages.
- `[YOUR_BACKEND_URL]/api/memory/clear` for clearing session memory.

**Note:** Replace `[YOUR_BACKEND_URL]` with your actual backend URL (e.g., `http://localhost:5000` for local development or your deployed backend URL).

If you need to change this (e.g., to point to a different backend or a locally running service), you'll need to update the `fetch` URLs in `src/components/chat/ChatBot.tsx`.

## How to Use

1.  Open the application in your browser.
2.  Type your message in the input field at the bottom of the chat window and press Enter or click the send button.
3.  Your message will appear in the chat, followed by a "thinking" indicator.
4.  The bot's response will then be displayed.
5.  To clear the conversation and start a new session, click the settings/clear icon in the chat header.

## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

Please make sure to update tests as appropriate.

## License

Consider adding a `LICENSE` file to your project (e.g., MIT License).

---

*This README was updated by an AI assistant. Please review and customize it further to accurately reflect your project.*
