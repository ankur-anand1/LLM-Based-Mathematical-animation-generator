import os
import time

from dotenv import load_dotenv
from google import genai
from google.genai import errors

load_dotenv()

client = genai.Client(
    api_key=os.environ["GEMINI_API_KEY"]
)

# Models are tried in order. If the first is overloaded (503), we fall back
# to the next one. gemini-2.0-flash is usually less busy than 2.5-flash.
MODELS = [
    "gemini-2.5-flash",
    "gemini-2.0-flash",
]

MAX_RETRIES = 5      # how many times to retry when the server is busy
WAIT_SECONDS = 5     # how long to wait between retries


def ask_gemini(prompt):
    last_error = None

    for model in MODELS:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                )
                return response.text

            except errors.ServerError as e:
                # 503 / overloaded -> wait and try again
                last_error = e
                print(
                    f"[gemini] {model} busy (attempt {attempt}/{MAX_RETRIES}). "
                    f"Waiting {WAIT_SECONDS}s and retrying..."
                )
                time.sleep(WAIT_SECONDS)

        print(f"[gemini] {model} kept failing. Trying next model...")

    # If we get here, every model and every retry failed.
    raise RuntimeError(
        "Gemini is overloaded right now (503). Tried all models and retries. "
        "Please run it again in a minute."
    ) from last_error
