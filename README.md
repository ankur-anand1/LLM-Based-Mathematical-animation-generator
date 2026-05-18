# Prompt-Based Mathematical Animation Generator

Turn a plain-English physics or math prompt into an animated Manim video.

```
User prompt  ->  Gemini (blueprint)  ->  OpenAI + RAG  ->  Manim  ->  MP4
                                              ^
                                              |____ self-repair loop ____|
```

## Features

- Natural-language prompt to rendered `.mp4`
- **Template router**: common topics (projectile, SHM, Faraday, etc.) use tested hand-written animations instantly
- **AI pipeline**: Gemini builds a scene blueprint; OpenAI generates Manim code with RAG context
- **Self-repair loop**: failed renders are sent back to the LLM with the error
- **Visual QA**: optional frame review to catch static or broken animations

## Project structure

```
.
├── make_animation.py              # Main entry point
├── download_manimbench.py         # Optional: download extra RAG examples
├── requirements.txt
├── .env.example                   # OpenAI key (copy to .env)
├── src/
│   ├── config.py
│   ├── prompts.py
│   ├── llm_client.py
│   ├── generator.py
│   ├── renderer.py
│   ├── retrieval.py
│   ├── rag_index.py
│   └── visual_qa.py
├── templates/                     # Hand-written, tested Manim templates
├── basis/                         # Reusable Manim building blocks
├── data/
│   └── manimbench.json            # Optional RAG corpus (417 examples)
└── physisyn2/object_deducer/      # Gemini blueprint module
    ├── gemini_client.py
    ├── validator.py
    ├── db/
    └── prompts/
```

## Setup (Windows)

1. **Install FFmpeg** (Manim needs it):
   ```powershell
   winget install Gyan.FFmpeg
   ```
   Restart your terminal, then verify: `ffmpeg -version`

2. **Install Python dependencies:**
   ```powershell
   python -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

3. **Add API keys:**
   ```powershell
   copy .env.example .env
   copy physisyn2\object_deducer\.env.example physisyn2\object_deducer\.env
   ```
   Edit both files and add your `OPENAI_API_KEY` and `GEMINI_API_KEY`.

   > Manim also needs LaTeX (e.g. [MiKTeX](https://miktex.org/)) for `MathTex`/`Tex`.
   > Without LaTeX, stick to `Text(...)` in prompts.

4. **(Optional) Download more RAG examples:**
   ```powershell
   python download_manimbench.py
   ```

## Usage

```powershell
python make_animation.py
# or with a prompt directly:
python make_animation.py "projectile motion with gravity"
```

Rendered videos are saved to the `output/` folder (created automatically).

## How it works

1. **Router** — If your prompt matches a keyword (projectile, SHM, Faraday, etc.), a tested template is rendered immediately with no API calls.
2. **Blueprint** — Otherwise, Gemini reads your prompt and produces a structured scene blueprint.
3. **Code generation** — OpenAI writes Manim code, boosted by RAG examples from templates and ManimBench.
4. **Self-repair** — If rendering fails, the error is fed back to the LLM for automatic fixes.
5. **Visual QA** — Key frames are checked to catch static or broken animations.

## Safety note

The renderer executes LLM-generated Python. It includes a basic keyword guard only.
For public deployment, run renders inside a container or sandbox.
