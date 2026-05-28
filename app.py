import os
import hashlib
import sqlite3
import stripe


from openai import OpenAI
from flask_htmx import HTMX
from dotenv import load_dotenv
from flask_hot_reload import HotReload
from flask import Flask, request, render_template


# load environment variables
load_dotenv()

# OpenAI instance
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
stripe.api_key = os.getenv("STRIPE_TEST_KEY")

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


def initialize_database():
    conn = sqlite3.connect("app.db")
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (fingerprint text primary key, usage_counter int)
        """
    )
    conn.commit()
    conn.close()


def get_fingerprint():
    browser = request.user_agent.browser
    version = request.user_agent.version and float(
        request.user_agent.version.split(".")[0]
    )
    platform = request.user_agent.platform
    string = f"{browser}:{version}:{platform}"
    fingerprint = hashlib.sha256(string.encode("utf-8")).hexdigest()
    print(fingerprint)
    return fingerprint


def get_usage_counter(fingerprint):
    with sqlite3.connect("app.db") as conn:
        c = conn.cursor()
        result = c.execute(
            'SELECT usage_counter FROM users WHERE fingerprint=?',
            (fingerprint,)
        ).fetchone()

        if result is None:
            c.execute(
                '''
                INSERT INTO users (fingerprint, usage_counter)
                VALUES (?, ?)
                ''',
                (fingerprint, 0)
            )
            return 0

        return result[0]


def update_usage_counter(fingerprint, usage_counter):
    with sqlite3.connect("app.db") as conn:
        c = conn.cursor()
        c.execute(
            '''
            UPDATE users
            SET usage_counter=?
            WHERE fingerprint=?
            ''',
            (usage_counter, fingerprint)
        )

        if c.rowcount == 0:
            raise ValueError("Fingerprint not found")


@app.route("/", methods = ["GET"])
def index():
    initialize_database()

    if htmx:
        return render_template("snippets/cleartextboxes.html")    
    return render_template("index.html")


@app.route("/submit", methods = ["POST"])
def submit():
    fingerprint = get_fingerprint()
    usage_counter = get_usage_counter(fingerprint)

    if not htmx:
        return render_template("index.html")    

    if usage_counter > 3:
        return render_template("payment.html")

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
        corrected_code_response = sections[1].strip()

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
