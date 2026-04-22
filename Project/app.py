from flask import Flask, render_template, request, redirect, jsonify, session, url_for
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
import random
import os
client_id = os.getenv("GOOGLE_CLIENT_ID")
client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

app = Flask(__name__)

# 🔐 SESSION CONFIG
app.secret_key = "super_secret_key_123"
app.config['SESSION_COOKIE_SAMESITE'] = "Lax"
app.config['SESSION_COOKIE_SECURE'] = False

# ---------------- GOOGLE AUTH ---------------- #
oauth = OAuth(app)

google = oauth.register(
    name='google',
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# ---------------- DATABASE ---------------- #
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///driving_data.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ---------------- MODELS ---------------- #
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100))
    fullname = db.Column(db.String(100))
    age = db.Column(db.String(10))
    aadhar = db.Column(db.String(20))
    vehicle = db.Column(db.String(20))

class Result(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_email = db.Column(db.String(100))
    theory = db.Column(db.Integer)
    simulator = db.Column(db.Integer)
    total = db.Column(db.Integer)

# ---------------- GOOGLE LOGIN ---------------- #
@app.route("/google-login")
def google_login():
    return google.authorize_redirect(
        url_for('google_callback', _external=True),
        prompt='select_account'   # ✅ FORCE account selection
    )

@app.route("/google-callback")
def google_callback():
    token = google.authorize_access_token()

    # ✅ FIXED URL
    resp = google.get('https://www.googleapis.com/oauth2/v3/userinfo')
    user = resp.json()

    email = user["email"]

    existing = User.query.filter_by(email=email).first()
    if not existing:
        db.session.add(User(email=email, password="google"))
        db.session.commit()

    session["user"] = email

    return redirect("/dashboard")
# ---------------- ROUTES ---------------- #
@app.route("/")
def home():
    return render_template("welcome.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if User.query.filter_by(email=email).first():
            return "Email already exists"

        user = User(email=email, password=password)
        db.session.add(user)
        db.session.commit()

        return redirect("/login")

    return render_template("register.html")

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = User.query.filter_by(email=email, password=password).first()

        if user:
            session["user"] = email
            return redirect("/dashboard")

        return "Invalid login ❌"

    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    return render_template("dashboard.html")

# ---------------- APPLICATION ---------------- #
@app.route("/application", methods=["GET","POST"])
def application():
    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":
        vehicle = request.form.get("vehicle")

        data = Application(
            user_email=session["user"],
            fullname=request.form.get("fullname"),
            age=request.form.get("age"),
            aadhar=request.form.get("aadhar"),
            vehicle=vehicle
        )

        db.session.add(data)
        db.session.commit()

        session["vehicle"] = vehicle

        return redirect("/face")

    return render_template("application.html")

# ---------------- FACE VERIFY ---------------- #
import base64, cv2, numpy as np
from deepface import DeepFace

# -------- FACE VERIFICATION -------- #
import base64
import cv2
import numpy as np
import os
from deepface import DeepFace
from flask import request, jsonify, session

@app.route("/verify_face", methods=["POST"])
def verify_face():

    passport_path = session.get("passport")

    if not passport_path or not os.path.exists(passport_path):
        return jsonify({"status": "❌ Upload passport photo first"})

    try:
        # 📸 Get live image
        data = request.json.get("image")

        if not data:
            return jsonify({"status": "❌ No image received"})

        image_data = base64.b64decode(data.split(',')[1])
        np_arr = np.frombuffer(image_data, np.uint8)
        live_img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if live_img is None:
            return jsonify({"status": "❌ Invalid camera image"})

        # 💾 Save live image
        temp_path = "static/faces/live.jpg"
        cv2.imwrite(temp_path, live_img)

        # 🔥 DeepFace verification (FIXED)
        result = DeepFace.verify(
            img1_path=passport_path,
            img2_path=temp_path,
            model_name="Facenet",             # ✅ better model
            detector_backend="retinaface",    # ✅ strong detector
            enforce_detection=True
        )

        print("RESULT:", result)

        distance = result["distance"]
        confidence = round((1 - distance) * 100, 2)

        # 🎯 Final decision
        if distance < 0.7:
            session["face_verified"] = True
            return jsonify({
                "status": "✅ Face Matched",
                "confidence": f"{confidence}%"
            })
        else:
            return jsonify({
                "status": "❌ Face Not Matching",
                "confidence": f"{confidence}%"
            })

    except Exception as e:
        print("ERROR:", str(e))
        return jsonify({"status": "❌ Face detection failed"})
    
@app.route("/upload_passport", methods=["POST"])
def upload_passport():
    file = request.files.get("file")

    if not file:
        return jsonify({"status": "❌ No file selected"})

    path = os.path.join("static/faces", "passport.jpg")
    file.save(path)

    session["passport"] = path

    return jsonify({"status": "✅ Passport uploaded"})
@app.route("/face")
def face():
    return render_template("verify.html")

@app.route("/face_done")
def face_done():
    if not session.get("face_verified"):
        return redirect("/face")

    return redirect("/slot")

# ---------------- SLOT ---------------- #
@app.route("/slot")
def slot():
    return render_template("slot.html")

# ---------------- THEORY ---------------- #
@app.route("/theory")
def theory():
    questions = [
        {"q":"Speed limit?","options":["40","60","80","100"],"ans":"60"},
        {"q":"Red signal?","options":["Go","Stop","Wait","Slow"],"ans":"Stop"},
        {"q":"Seat belt?","options":["Optional","Safety","None","Fashion"],"ans":"Safety"},
        {"q":"Helmet?","options":["Optional","Mandatory","None","Fashion"],"ans":"Mandatory"},
        {"q":"Overtake?","options":["Left","Right","Anywhere","None"],"ans":"Right"}
    ]

    return render_template("theory.html", questions=questions)

@app.route("/submit_theory", methods=["POST"])
def submit_theory():
    session["theory_done"] = True
    return jsonify({"status":"ok"})

# ---------------- SIMULATOR MODE SAVE ---------------- #
@app.route("/set_mode", methods=["POST"])
def set_mode():
    data = request.json
    session["mode"] = data.get("mode", "good")
    return jsonify({"status":"ok"})

# ---------------- SIMULATOR ---------------- #
@app.route("/simulator")
def simulator():
    if not session.get("theory_done"):
        return redirect("/theory")
    return render_template("simulator.html")

# ---------------- RESULT ---------------- #
@app.route("/result")
def result():

    mode = session.get("mode", "bad")   # 🔥 default = bad (safe)

    if mode == "bad":
        theory_score = random.randint(30, 50)
        sim_score = random.randint(20, 45)
    else:
        theory_score = random.randint(80, 95)
        sim_score = random.randint(75, 90)

    total = (theory_score + sim_score) // 2

    session["result_status"] = "PASS" if total >= 60 else "FAIL"

    return render_template("result.html",
                           theory=theory_score,
                           sim=sim_score,
                           total=total,
                           status=session["result_status"])

# ---------------- LOGOUT ---------------- #
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- RUN ---------------- #
if __name__ == "__main__":
    if not os.path.exists("static/faces"):
        os.makedirs("static/faces")

    with app.app_context():
        db.create_all()

    app.run(debug=True)