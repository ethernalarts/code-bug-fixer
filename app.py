import os

from openai import OpenAI
from flask_htmx import HTMX
from flask_hot_reload import HotReload
from flask import Flask, request, render_template

# OpenAI instance
client = OpenAI(api_key=os.get_env("API_KEY"))

# Flask instance
app = Flask(__name__)

# HTMX instance
htmx = HTMX(app)

# Browser Reload instance
hot_reload = HotReload(
    app, 
    includes=[
        'templates',
        'static',
    ],
    excludes=[
        '__pycache__',
        'node_modules',
        '.git',
        '.db'
    ]
)


@app.route("/", methods = ["GET"])
def index():
    if htmx:
        return render_template("snippets/cleartextboxes.html")
    
    return render_template("index.html")


@app.route("/submit", methods = ["POST"])
def submit():
    if not htmx or not code or not error_message:
        return render_template("index.html")
        
    code = request.form.get("code")
    error_message = request.form.get("error_message")    

    prompt = f"""
    Explain this error and fix the code.

    Code
    {code}

    Error
    {error_message}

    Respond in this format:

    Explanation:
    <error explanation>

    Fixed Code:
    <fixed code>
    """

    try:        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "user", "content": f"{prompt}"}
            ],
            max_tokens=1024,
            n=1,
            stop=None,
            temperature=0.2
        )

        content = response.choices[0].message.content
        sections = content.split("Explanation:")[1].split("Fixed Code:")
        error_explanation_response = sections[0].strip()
        corrected_code_response = sections[1].strip() if len(sections) > 1 else ""

        return render_template(
            "snippets/textareas.html",
            error_explained=error_explanation_response,
            corrected_code=corrected_code_response
        )
    
    except Exception as e:
        return render_template(
            "snippets/textareas.html",
            error_explained=f"Error explanation could not be generated: {str(e)}",
            corrected_code=f"Corrected code could not be generated: {str(e)}"
        )  


# @app.route("/clear", methods = ["GET"])
# def clear():
#     return render_template("snippets/cleartextboxes.xhtml")


if __name__ == "__main__":
    app.run(debug = True)
