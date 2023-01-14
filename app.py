import os
import openai
from flask import Flask, redirect, render_template, request, url_for, session, jsonify, abort
import re
from flask_dance.contrib.google import make_google_blueprint, google
from google.oauth2.credentials import Credentials

app = Flask(__name__)
app.secret_key = "your secret key"

# create the blueprint for google auth
google_bp = make_google_blueprint(
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    scope=["openid", "email", "profile"],
    redirect_url='http://127.0.0.1:5000/callback'
)
app.register_blueprint(google_bp, url_prefix="/login")

# check if user is logged in


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))
        else:
            return function(*args, **kwargs)
    return wrapper


@app.route("/")
def index():
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    return jsonify(resp.json())


@app.route("/login")
def login():
    return redirect(url_for("google.login"))


@app.route("/callback")
def callback():
    google.authorized_response()
    creds = Credentials.from_authorized_response(
        google.authorized_response(), scopes=google_bp.scopes)

    id_info = creds.id_token
    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/input")




@app.route("/input", methods=["GET", "POST"])
@login_is_required
def input():
    if request.method == "POST":
        title = request.form["animal"]
        response = openai.Completion.create(
            model="text-davinci-003",
            prompt=generate_list_title(title),
            temperature=0.5,
            max_tokens=2048,
            top_p=1
        )
        li = response.choices[0].text.strip().split("\n")
        result = [re.sub(r'^\d+\.', '', item).strip() for item in li]
        print(result)
        return render_template("input.html", results=result)

    return render_template("input.html", results=None)


@login_is_required
@app.route("/content/<slide_title>", methods=["GET"])
def content(slide_title):
    response = openai.Completion.create(
        model="text-davinci-003",
        prompt=generate_contnet(slide_title),
        temperature=0.5,
        max_tokens=2048,
        top_p=1
    )
    result = response.choices[0].text.strip()
    print(result)
    return render_template("content.html", content=result)


def generate_prompt(title):
    return f""" generate the ppt content slide by slide with titles on the topic {title} in json type with slide  number as key and slide data as value of that key"""


def generate_title(title):
    return f"""provide me a list of presentation slides on the topic {title}. Each slide should include a slide_{{number}} as the key, a title, and the data as the values. it have 8 slides must be in JSON format"""


def generate_list_title(title):
    return f"""generate just titles of slides presentation on the topic {title} it has 8 slides,"""


def generate_contnet(slide_title):
    return f"""generate the paragraph on the topic {slide_title})"""


if __name__ == "__main__":
    app.run(host='0.0.0.0', debug=True)
