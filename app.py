import os
import openai
from flask import Flask, redirect, render_template, request, url_for,session, jsonify,abort
import re
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from pip._vendor import cachecontrol
import google.auth.transport.requests
import requests
import pathlib


app = Flask(__name__)
app.secret_key = "<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>" # make sure this matches with that's in client_secret.json

os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1" # to allow Http traffic for local dev

GOOGLE_CLIENT_ID = "1066115487875-h22uq158e9f37d0uq23dgbmuacjockug.apps.googleusercontent.com"
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")

flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


def login_is_required(function):
    def wrapper(*args, **kwargs):
        if not google.authorized:
            return redirect(url_for("google.login"))
        else:
            return function(*args, **kwargs)
    return wrapper


@app.route("/login")
def login():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )

    session["google_id"] = id_info.get("sub")
    session["name"] = id_info.get("name")
    return redirect("/input")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/")
def index():
    return "Hello login ->> <a href='/login'><button>Login</button></a>"

@app.route("/input", methods=["GET","POST"])
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