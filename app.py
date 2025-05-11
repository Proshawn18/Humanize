import os
from flask import Flask, render_template, request, jsonify, flash, redirect, url_for

from google import genai
from google.genai import types

from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "change_this!"

# === Your “master” prompt and the active prompt ===
originalPrompt = (
    "Re-elaborate on the following AI-generated text, aiming to make it sound like a naturally "
    "flowing piece of human writing. Incorporate a blend of personal reflections, informal language, "
    "rhetorical questions, and moments of slight digression or tangential thoughts that eventually loop "
    "back to the main point. Inject subjective opinions and make it clear that this is one person's perspective on the topic.\n\n"
    "Here is the text:"
)
currentPrompt = originalPrompt  # will be swapped only when “broken” is reported

# === Gemini / Google Generative AI setup ===
client = genai.Client(api_key="AIzaSyAR4-y801Hu2fZAMBrntOLxvmfqbUL3f5s")
GEMINI_MODEL = "gemini-1.5-pro"  # example; use free-tier model

# === Limits ===
MAX_TEXT_CHARS = 10_000
MAX_FILE_BYTES = 1_000_000  # 1 MB

def generate_undetectable_text(user_input: str) -> str:
    full_prompt = f"{currentPrompt}\n\nUser text:\n{user_input}"
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=full_prompt
    )
    return response.text

def regenerate_prompt_via_gemini() -> str:
    """meta_prompt = (
        "You are a prompt engineer. Here is a prompt:\n\n"
        f"{originalPrompt}\n\n"
        "Analyze it for any weaknesses in producing undetectable AI text, "
        "improve it to be as strong and foolproof as possible, "
        "and return only the improved prompt. Do this evaluation iteratively "
        "to ensure robustness."
    )"""
    meta_prompt = f"""
Your task is to generate a new prompt for a large language model (LLM) that will instruct it to revise AI-generated text in a way that makes it more likely to be classified as human-written by multiple AI detection tools. The goal is for the revised text to consistently score below 35% AI probability on these detectors, even for texts ranging from a few hundred to a thousand words.
Here is the previous prompt:

{{currentPrompt}}

The new prompt you create should consider and incorporate strategies that mimic human writing styles and characteristics that AI detectors often look for. These strategies might include, but are not limited to:
* Specific instructions on incorporating diverse human-like elements: Think beyond just "informal language." Consider instructing the LLM to add specific types of personal anecdotes (e.g., brief, slightly embarrassing moments; observations about everyday life), subtle expressions of emotions tied to the content, and natural-sounding hesitations or self-corrections.
* Emphasis on subjective interpretation and personal voice: How can the prompt encourage the LLM to truly "own" the revised text and present it as a genuine human perspective, rather than just rephrasing?
* Techniques for varying sentence structure and rhythm in unpredictable ways: Human writing isn't always grammatically perfect or uniformly structured. How can the prompt encourage a more organic flow with intentional variations?
* Guidance on injecting subtle inconsistencies or minor "human errors" that feel natural: This is a delicate balance, but how can the prompt suggest incorporating imperfections that don't read as obviously AI-generated mistakes?
* Instructions on focusing on the "why" and "how" behind the original text, rather than just the "what": Can the prompt encourage the LLM to explore the underlying reasoning or implications in a more human-centric way?
* Consideration of different writing styles and contexts: Could the prompt suggest tailoring the revisions to sound like a specific type of human writing and preferably find a prevalent style or tone in the writing and stick to it in a natural way (e.g., a casual blog post, a heartfelt email, a slightly academic but still personal essay)?

The prompt you generate should be clear, concise, and actionable for an LLM. It should provide specific guidance rather than vague instructions. Do not include any AI-generated text examples in your response. Your sole task is to create a new prompt that aims to improve the "human-detectability" of revised AI text.
"""
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=meta_prompt
    )
    return response.text.strip()


# === Routes ===

@app.route("/", methods=["GET", "POST"])
def index():
    # Common context for template
    context = {
        "MAX_TEXT_CHARS": MAX_TEXT_CHARS,
        "MAX_FILE_BYTES": MAX_FILE_BYTES
    }

    if request.method == "POST":
        action = request.form.get("action")

        if action == "generate":
            user_text = request.form.get("user_text", "")
            uploaded = request.files.get("user_file")

            if uploaded:
                data = uploaded.read()
                if len(data) > MAX_FILE_BYTES:
                    flash(f"File too large (max {MAX_FILE_BYTES // 1_000_000} MB).", "danger")
                    return render_template("index.html", **context)
                user_text = data.decode(errors="ignore")

            if len(user_text) > MAX_TEXT_CHARS:
                flash(f"Text too long (max {MAX_TEXT_CHARS} chars).", "danger")
                return render_template("index.html", **context)

            result = generate_undetectable_text(user_text)
            context["result"] = result
            return render_template("index.html", **context)

        elif action == "report_broken":
            global currentPrompt
            currentPrompt = regenerate_prompt_via_gemini()
            flash("Prompt has been regenerated and updated.", "success")
            # After regenerating, just re-render the form
            return render_template("index.html", **context)

    # GET request
    return render_template("index.html", **context)



if __name__ == "__main__":
    app.run(debug=True)