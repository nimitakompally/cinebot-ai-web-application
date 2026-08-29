# cinebot-ai-web-application

# CineBot 🎬

A movie recommendation chatbot. Tell it what mood you're in and it talks back with three picks, styled like little ticket stubs.

## How it works

You type something like "I want a cozy sci-fi movie" and it goes to a FastAPI backend, which sends your message (plus the whole conversation so far) to an LLM. The backend forces the model to respond in a strict JSON shape — a reply message plus a list of movies with title, year, genre, and a reason — and Pydantic validates that shape before it ever reaches the frontend. The frontend is plain JS: no framework, just DOM manipulation and a `fetch` call.

Conversation memory isn't stored anywhere on the backend — the frontend keeps the running history in an array and resends the whole thing with every message, so the model has context each time.

## Stack

- **Backend:** Python, FastAPI, Pydantic
- **LLM:** Groq API (`llama-3.3-70b-versatile`), called through the OpenAI SDK pointed at Groq's endpoint since it's a drop-in-compatible API
- **Frontend:** HTML, CSS, vanilla JavaScript

## Running it locally

You'll need a [Groq API key](https://console.groq.com).

```bash
cd cinebot-project
export GROQ_API_KEY="your-key-here"
pip install fastapi uvicorn openai
uvicorn cinebot:app --reload
```

Then just open `index.html` in your browser. That's it — no build step, no frontend server.

## Notes

Built as a way to get hands-on with structured LLM output and prompt engineering — forcing a model to reliably return valid JSON turned out to be the trickiest part, not the chat UI itself.
