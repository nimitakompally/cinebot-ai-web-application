# ── Imports ──────────────────────────────────────────────────────────────────

# FastAPI is the framework that runs our server
# HTTPException lets us send proper error responses (like 404, 500) instead of crashing
from fastapi import FastAPI, HTTPException

# BaseModel is from Pydantic - we inherit from it to define the shape of our data
# Pydantic automatically validates incoming data and rejects anything wrong
from pydantic import BaseModel

# Optional means a field doesn't have to be included in the request
# If it's left out, it just uses the default value we set
from typing import Optional

# OpenAI is the client class we use to talk to the OpenAI API
from openai import OpenAI

# json is built into Python - we need it to convert the AI's raw text response
# into an actual Python dictionary we can work with
import json

# os lets us read environment variables, like our GROQ_API_KEY
import os

# CORSMiddleware allows our HTML/JS frontend (running on a different port/origin)
# to make requests to this API. Without it, the browser blocks the request.
from fastapi.middleware.cors import CORSMiddleware


# ── App and client setup ──────────────────────────────────────────────────────

# This creates our server - think of it as the building that holds all our endpoints
# When we run "uvicorn main:app", uvicorn looks for this "app" variable
app = FastAPI()

# This allows our frontend (index.html/script.js) to call this API from the
# browser. allow_origins=["*"] is fine for local development/testing.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# This creates our connection to the AI API.
# We're using the OpenAI SDK, but pointing it at Groq's servers instead of
# OpenAI's, since Groq's API is built to be a drop-in replacement for
# OpenAI's - same request/response format, just a different base_url and key.
# It reads our GROQ_API_KEY from environment variables.
client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ.get("GROQ_API_KEY"),
)


# ── Pydantic models (shapes of our data) ─────────────────────────────────────

# This defines what must come IN when someone calls POST /chat
# It's like a contract - the request must match this shape or it gets rejected
class ChatRequest(BaseModel):
    message: str                       # required - the user's current message (must be a string)
    conversation_history: Optional[list] = []  # optional - list of previous messages
                                               # defaults to empty list if not provided


# This defines what goes OUT when our endpoint responds
# FastAPI will automatically format our return value to match this shape
class ChatResponse(BaseModel):
    reply: str                   # the AI's text response to the user
    movies: Optional[list] = []  # list of movie recommendations (can be empty)


# ── System prompt ─────────────────────────────────────────────────────────────

# This is the instructions we give the AI before any user message is sent
# It uses the "system" role - the AI reads this first before anything else
# Triple quotes """ let us write a string across multiple lines
SYSTEM_PROMPT = """
You are a movie recommendation assistant.
When a user describes their taste or mood, recommend 3 movies.

Always respond in this exact JSON format:
{
  "reply": "A short friendly message to the user",
  "movies": [
    {
      "title": "Movie Title",
      "year": 2020,
      "genre": "Genre",
      "reason": "Why this matches what they said"
    }
  ]
}

If the user says something unrelated to movies, set movies to []
and just reply normally in the reply field.
Always return valid JSON and nothing else.
"""
# The last line "Always return valid JSON and nothing else" is critical
# Without it, the AI might add extra sentences like "Sure! Here you go: {...}"
# That would break our json.loads() call later because it wouldn't be pure JSON


# ── POST /chat endpoint ───────────────────────────────────────────────────────

# This decorator tells FastAPI: when someone sends a POST request to /chat, run this function
# response_model=ChatResponse tells FastAPI to validate our return value against ChatResponse
@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    # FastAPI already validated the request and gave us it as the "request" variable
    # So request.message is the user's message, request.conversation_history is the history

    # Step 1: Start building the messages list
    # This is the format the OpenAI API requires - a list of dictionaries
    # Each dictionary has "role" (who is speaking) and "content" (what they said)
    # We always put the system prompt first so the AI reads its instructions before anything else
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Step 2: Add all previous messages from the conversation
    # LLMs have no memory between API calls - every call starts fresh
    # So we re-send the entire conversation history every time to fake memory
    # Without this loop, the AI would forget everything said before this message
    for msg in request.conversation_history:
        messages.append(msg)

    # Step 3: Add the user's new message at the very end
    # Order matters - history first, new message last
    # The AI reads top to bottom like a chat log, so the newest message must be last
    messages.append({"role": "user", "content": request.message})

    # At this point "messages" looks like:
    # [
    #   {"role": "system",    "content": "You are a movie assistant..."},  <- instructions
    #   {"role": "user",      "content": "I like sci-fi"},                 <- old message
    #   {"role": "assistant", "content": "Try Interstellar!"},             <- old AI reply
    #   {"role": "user",      "content": "anything with time travel?"}     <- newest message
    # ]

    # Step 4: Send the messages list to the API and wait for a response
    # model="llama-3.3-70b-versatile" specifies which AI model to use on Groq
    # messages=messages passes the full list we just built
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages
    )

    # Step 5: Pull out the AI's text from the response object
    # The API returns a big object - .choices is a list of possible responses
    # [0] gets the first one (there's usually only one)
    # .message.content is the actual text the AI wrote
    # At this point "raw" is a plain string like: '{"reply": "...", "movies": [...]}'
    raw = response.choices[0].message.content

    # Step 6: Convert the raw string into a Python dictionary and return it
    # "try" means attempt this - if something goes wrong, go to "except" instead of crashing
    try:
        # json.loads() converts a JSON string into a Python dictionary
        # e.g. '{"reply": "hello"}' becomes {"reply": "hello"} - now we can use data["reply"]
        data = json.loads(raw)

        # Pull out the fields and wrap them in our ChatResponse model to send back
        # data.get("movies", []) is safer than data["movies"] because
        # if "movies" key is missing for some reason, it returns [] instead of crashing
        return ChatResponse(reply=data["reply"], movies=data.get("movies", []))

    except json.JSONDecodeError:
        # If the AI returned something that wasn't valid JSON (e.g. added an extra sentence),
        # json.loads() throws a JSONDecodeError - we catch it here
        # Instead of crashing the whole server, we send back a clean 500 error
        raise HTTPException(status_code=500, detail="Model returned invalid JSON")


# ── GET / endpoint ────────────────────────────────────────────────────────────

# A simple health check - visiting the base URL confirms the API is running
@app.get("/")
def root():
    return {"message": "CineBot API is running"}