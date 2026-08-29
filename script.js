// ── Config ─────────────────────────────────────────────────────────
// This is the address of your FastAPI backend (cinebot.py / main.py).
// When you run it locally with `uvicorn main:app --reload`, it serves
// on this address by default. Change this if you deploy it elsewhere.
const API_URL = "http://127.0.0.1:8000/chat";

// ── Grab references to the HTML elements we'll need to update ──────
// document.getElementById() finds an element by its id="" attribute.
// We save each one in a variable so we don't have to look it up again.
const chatWindow = document.getElementById("chat-window");
const chatForm = document.getElementById("chat-form");
const userInput = document.getElementById("user-input");

// ── Conversation memory ──────────────────────────────────────────
// The backend has no memory of its own between requests (see the
// comments in main.py). So the FRONTEND is responsible for keeping
// track of the conversation and sending the whole history back every
// time. This array grows as the conversation continues.
// Each entry looks like: { role: "user" or "assistant", content: "..." }
let conversationHistory = [];

// ── Listen for the form being submitted (Send button OR Enter key) ──
chatForm.addEventListener("submit", async (event) => {
  // Forms normally reload the page on submit - this stops that.
  event.preventDefault();

  // Read whatever the user typed, and trim() removes extra spaces.
  const userMessage = userInput.value.trim();
  if (!userMessage) return; // ignore empty submissions

  // Show the user's message in the chat window immediately.
  addMessageBubble(userMessage, "user");

  // Clear the input box so it's ready for the next message.
  userInput.value = "";

  // Show a temporary "thinking..." bubble while we wait for the API.
  const loadingBubble = addMessageBubble("Thinking...", "bot loading");

  try {
    // Send the message + full history to the backend.
    const data = await sendToBackend(userMessage);

    // Remove the "Thinking..." bubble now that we have a real reply.
    loadingBubble.remove();

    // Show CineBot's text reply.
    addMessageBubble(data.reply, "bot");

    // If CineBot recommended movies, show them as ticket-style cards.
    if (data.movies && data.movies.length > 0) {
      addMovieCards(data.movies);
    }

    // Update our running history so the next message has full context.
    conversationHistory.push({ role: "user", content: userMessage });
    conversationHistory.push({ role: "assistant", content: data.reply });

  } catch (error) {
    // If the fetch failed (server down, network error, bad JSON, etc.)
    // show a friendly error message instead of crashing silently.
    loadingBubble.remove();
    addMessageBubble(
      "Sorry, something went wrong talking to the server. Is the backend running?",
      "bot"
    );
    console.error("CineBot request failed:", error);
  }
});

// ── Talks to the FastAPI /chat endpoint ──────────────────────────
// "async function" means this function can use "await" inside it to
// pause until a slow operation (like a network request) finishes.
async function sendToBackend(userMessage) {
  // fetch() sends an HTTP request. We POST because we're sending data,
  // not just asking for a page.
  const response = await fetch(API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json", // tells the server we're sending JSON
    },
    // The backend's ChatRequest model expects exactly these two fields:
    // { message: string, conversation_history: list }
    body: JSON.stringify({
      message: userMessage,
      conversation_history: conversationHistory,
    }),
  });

  // If the server responded with an error status (like 500), throw so
  // our catch block above handles it instead of silently continuing.
  if (!response.ok) {
    throw new Error(`Server responded with status ${response.status}`);
  }

  // .json() parses the response body from JSON text into a JS object.
  // This matches the backend's ChatResponse shape: { reply, movies }
  return response.json();
}

// ── Adds a plain text chat bubble to the window ──────────────────
// className can be "user", "bot", or "bot loading" (loading adds a
// second CSS class for the italic "Thinking..." style).
function addMessageBubble(text, className) {
  const bubble = document.createElement("div");
  bubble.className = `message ${className}`;

  const paragraph = document.createElement("p");
  paragraph.textContent = text; // textContent (not innerHTML) avoids XSS risk
  bubble.appendChild(paragraph);

  chatWindow.appendChild(bubble);

  // Auto-scroll to the newest message.
  chatWindow.scrollTop = chatWindow.scrollHeight;

  return bubble; // returned so we can remove() the loading bubble later
}

// ── Adds the 3 recommended movies as ticket-style cards ───────────
function addMovieCards(movies) {
  // movies.forEach runs the given function once per movie in the list.
  movies.forEach((movie) => {
    const card = document.createElement("div");
    card.className = "movie-card";

    // template literals (backticks) let us insert variables with ${...}
    card.innerHTML = `
      <h3>${escapeHTML(movie.title)} (${escapeHTML(String(movie.year))})</h3>
      <p class="meta">${escapeHTML(movie.genre)}</p>
      <p class="reason">${escapeHTML(movie.reason)}</p>
    `;

    chatWindow.appendChild(card);
  });

  chatWindow.scrollTop = chatWindow.scrollHeight;
}

// ── Small safety helper ───────────────────────────────────────────
// Escapes special HTML characters so movie data from the API can never
// accidentally be interpreted as HTML/script tags (basic XSS safety).
function escapeHTML(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
