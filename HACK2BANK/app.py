from flask import Flask, render_template, request, jsonify
import json
from flask import Flask, render_template, request, session, redirect, url_for, flash, send_file,send_from_directory,jsonify
from flask_socketio import join_room, leave_room, send, SocketIO
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, ValidationError
import bcrypt
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from flask_mail import Mail, Message
from geopy.distance import geodesic
import pandas as pd
from tensorflow.keras.models import load_model
import numpy as np
import pickle
import random
from flask_babel import Babel, _

app = Flask(__name__)
app.config["SECRET_KEY"] = "your_secret_key_here"

# Load chatbot conversation data
with open('data/conversation_data.json', 'r') as file:
    conversation_data = json.load(file)

# Extract official links for fraud detection
official_links = conversation_data.get("official_links", [])

@app.route('/')
def home():
    return render_template('index.html')
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'mydatabase'
mysql = MySQL(app)

rooms = {}
meeting_rooms = set()

class RegisterForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired()])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Register")

    def validate_email(self, field):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (field.data,))
        user = cursor.fetchone()
        cursor.close()
        if user:
            raise ValidationError('Email Already Taken')

class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        cursor = mysql.connection.cursor()
        cursor.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed_password))
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('login'))

    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email=%s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and bcrypt.checkpw(password.encode('utf-8'), user[3].encode('utf-8')):
            session['user_id'] = user[0]
            return redirect(url_for('dashboard'))
        else:
            flash("Login failed. Please check your email and password")
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/TopBanks')
def TopBanks():
    return  render_template('TopBanks.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/SMSFraudReport')
def SMsFraudReport():
    return render_template('SMSfraud.html')

@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')
@app.route('/support')
def support():
    return render_template('support.html')

@app.route('/Loans')
def loans():
    return render_template('Loans.html')
@app.route('/Quiz')
def Quiz():
    return render_template('Quiz.html')

# Load the trained model and TF-IDF vectorizer
model = load_model('fraud_detection_model.h5')
with open('tfidf_vectorizer.pkl', 'rb') as f:
    vectorizer = pickle.load(f)
def predict():
    try:
        # Get URL from the form
        url = request.form['url']
        
        # Vectorize the input URL
        url_tfidf = vectorizer.transform([url]).toarray()
        
        # Make prediction
        prediction = model.predict(url_tfidf)
        result = 'NOT FAKE' if prediction[0][0] > 0.5 else 'FAKE'
        
        return  result
    
    except Exception as e:
        return ({'error': str(e)}), 400

@app.route('/get_response', methods=['POST'])

def get_response():
    user_input = request.json.get('user_input', '').lower()  # Get user input

    # Handle fraud detection
    if user_input == "fraud detection":
        return jsonify({
            "response": "Please enter the link you want to verify.",
        })

    # If the user provides a link for verification
    if  user_input.startswith("https://") or user_input.startswith("http://") :
        if  user_input.startswith("https://"):    
            return jsonify({
                "response": "This is an official and safe link.",
                "options": ["Hi", "Bye"]
            })
        else:
            # predict(user_input)
            return jsonify({
                "response": "Warning: This link is not in our list of official links. Proceed with caution!",
                "options": ["Hi", "Bye"]
            })

    # Normal chatbot responses from JSON
    elif user_input in conversation_data:
        response = conversation_data[user_input]
        return jsonify({
            "response": response["response"],
            "options": response["options"]
        })
    
    # Default response if input is unrecognized
    else:
        return jsonify({
        "response": "I don't understand that. Please try something else.",
        "options": ["Hi", "Bye"]
    })

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    flash("You have been logged out successfully.")
    return redirect(url_for('login'))


@app.route('/LoanEligibility')
def loanEligibility():
    return render_template('LoanEligibilityChecker.html')

mail = Mail(app)
scheduler = BackgroundScheduler()

# MySQL connection
# def get_db_connection():
#     connection = mysql.connector.connect(
#         host='localhost',
#         user='root',
#         password='',  # Default XAMPP password for MySQL is empty
#         database='hack2bank_db'  # Name of your database
#     )
#     return connection

@app.route('/bill')
def bill_reminder():
    return render_template('bill_index.html')

app.config["SECRET_KEY"] = "your_secret_key_here"
app.config['MAIL_SERVER'] = 'smtp.gmail.com'  # Or your mail server if not using Gmail
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '2203031240976@paruluniversity.ac.in'  # Use your college email here
app.config['MAIL_PASSWORD'] = 'Palinakarthik@18'  # Your email password (or app password if 2FA enabled)
app.config['MAIL_DEFAULT_SENDER'] = '2203031240976@paruluniversity.ac.in'  # Same as above

mail = Mail(app)

scheduler = BackgroundScheduler()
scheduler.start()

@app.route('/set_bill_reminder', methods=['POST'])
def set_bill_reminder():
    data = request.json
    bill_name = data.get('bill_name')
    amount = data.get('amount')
    due_date = data.get('due_date')
    user_email = 'user@example.com'  # Replace with actual user's email (e.g., from session)

    # Store bill details in your database (you'll need to implement the database logic)
    
    # Schedule reminder task
    due_date_obj = datetime.strptime(due_date, "%Y-%m-%d")
    reminder_time = due_date_obj - timedelta(days=1)
    scheduler.add_job(func=send_reminder, trigger='date', run_date=reminder_time, args=[user_email, bill_name, amount, due_date])

    return jsonify({"message": "Bill reminder set successfully!"})

def send_reminder(user_email, bill_name, amount, due_date):
    # Send reminder email
    msg = Message(
        'Bill Payment Reminder',
        recipients=[user_email]
    )
    msg.body = f"Reminder: Your {bill_name} bill of ${amount} is due on {due_date}. Please make the payment soon."
    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email: {e}")



# Load mock registered entities database
with open('data/entities.json', 'r') as file:
    entities_data = json.load(file)

@app.route('/IChecker', methods=['GET', 'POST'])
def IChecker():
    result = None
    if request.method == 'POST':
        entity_name = request.form['entityName']
        
        # Mock logic for checking the entity
        registered_entities = [
            "SafeInvest Corp", 
            "Future Secure LLP", 
            "GrowthTrust Investments",
            "WealthMax Solutions", 
            "SecureReturns Co."
        ]
        
        if entity_name in registered_entities:
            result = {
                'class': 'valid',
                'message': f'{entity_name} is a registered and legitimate entity.'
            }
        else:
            result = {
                'class': 'invalid',
                'message': f'{entity_name} is not found in our registered entities database. Please exercise caution!'
            }
    return render_template('I_Checker.html', result=result)

# Load bank data from CSV
BANKS_FILE = "banks.csv"
banks_df = pd.read_csv(BANKS_FILE)

@app.route("/NearbyBanks")
def NearbyBanks():
    return render_template("NearbyBanks.html")

@app.route('/find_banks', methods=['POST'])
def find_banks():
    try:
        # Parse the request data
        data = request.get_json()
        latitude = data['latitude']
        longitude = data['longitude']

        # OpenStreetMap Overpass API URL
        overpass_url = "http://overpass-api.de/api/interpreter"
        overpass_query = f"""
        [out:json];
        node["amenity"="bank"](around:10000,{latitude},{longitude});
        out;
        """
        response = request.get(overpass_url, params={'data': overpass_query})
        response.raise_for_status()

        # Parse response
        data = response.json()
        banks = data.get('elements', [])

        # Extract bank details
        result = [
            {
                "Bank Name": bank.get("tags", {}).get("name", "Unnamed Bank"),
                "Latitude": bank["lat"],
                "Longitude": bank["lon"]
            }
            for bank in banks
        ]

        if not result:
            return jsonify({"message": "No banks found within 10 km."})

        return jsonify(result)

    except Exception as e:
        return jsonify({"error": str(e)}), 400
     
@app.route('/Subs')
def subs():
    return render_template('subs.html')







if __name__ == '__main__':
    app.run(debug=True)
