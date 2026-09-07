"""
FoodLink — Flask backend (app.py)

Serves the static frontend (the .html/.css/.js files in this same
folder) AND exposes a small JSON API under /api/... that the
frontend's js/script.js calls with fetch().

Run with:  python app.py
Then open: http://localhost:5000/index.html

Uses the exact same foodlink_db.sql schema as before — nothing
about the database changes, only how it's queried (Python instead
of PHP).
"""

from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import re
import os
import joblib
import pandas as pd

app = Flask(__name__, static_folder='.', static_url_path='')

# IMPORTANT: change this to any random string before real use.
app.secret_key = 'change-this-secret-key'

# ---------------------------------------------------------
# AI/ML: "Estimated People Fed" model
# Trained by ml/train_model.py on a synthetic dataset
# (ml/generate_dataset.py). Loaded once here at startup so
# every request reuses the same in-memory model.
# ---------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml', 'model.pkl')
try:
    people_fed_model = joblib.load(MODEL_PATH)
    print('Loaded people-fed prediction model.')
except Exception as e:
    people_fed_model = None
    print('Could not load ML model (predictions will be skipped):', e)


def predict_people_fed(quantity, unit, category, food_type):
    """Returns a predicted integer, or None if the model isn't loaded."""
    if people_fed_model is None:
        return None
    try:
        row = pd.DataFrame([{
            'quantity': float(quantity),
            'unit': unit,
            'category': category,
            'food_type': food_type,
        }])
        prediction = people_fed_model.predict(row)[0]
        return max(1, round(float(prediction)))
    except Exception:
        return None

# ---------------------------------------------------------
# Database connection settings
# Update DB_USER / DB_PASS to match what you use in
# MySQL Workbench to connect to your local server.
# ---------------------------------------------------------
import os

DB_HOST = os.environ.get('DB_HOST', '127.0.0.1')
DB_PORT = int(os.environ.get('DB_PORT', '3306'))
DB_USER = os.environ.get('DB_USER', 'root')
DB_PASS = os.environ.get('DB_PASSWORD', 'root')
DB_NAME = os.environ.get('DB_NAME', 'foodlink_db')
#

EMAIL_PATTERN = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')
PHONE_PATTERN = re.compile(r'^[0-9]{10}$')


def get_db():
    return mysql.connector.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, database=DB_NAME,
        ssl_disabled=False
    )




# ---------------------------------------------------------
# Serve the frontend
# ---------------------------------------------------------
@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')


# ===========================================================
# SESSION
# ===========================================================
@app.route('/api/session')
def api_session():
    if session.get('donor_id'):
        return jsonify(loggedIn=True, role='donor', name=session.get('donor_name'))
    if session.get('receiver_id'):
        return jsonify(loggedIn=True, role='receiver', name=session.get('receiver_name'))
    if session.get('volunteer_id'):
        return jsonify(loggedIn=True, role='volunteer', name=session.get('volunteer_name'))
    return jsonify(loggedIn=False)


@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify(message='Logged out.')


# ===========================================================
# DONOR: register / login
# ===========================================================
@app.route('/api/donor/register', methods=['POST'])
def donor_register():
    data = request.get_json(silent=True) or {}
    business_name = (data.get('business_name') or '').strip()
    owner_name = (data.get('owner_name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    fssai_number = (data.get('fssai_number') or '').strip()
    gstin = (data.get('gstin') or '').strip() or None
    address = (data.get('address') or '').strip()
    city = (data.get('city') or '').strip()
    password = data.get('password') or ''
    confirm = data.get('confirm_password') or ''

    if not all([business_name, owner_name, email, phone, fssai_number, address, city, password]):
        return jsonify(error='Please fill in all required fields.'), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify(error='Please enter a valid email address.'), 400
    if not PHONE_PATTERN.match(phone):
        return jsonify(error='Please enter a valid 10-digit phone number.'), 400
    if len(password) < 6 or password != confirm:
        return jsonify(error='Passwords must match and be at least 6 characters.'), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id FROM donors WHERE email = %s', (email,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify(error='That email is already registered.'), 400

    hashed = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO donors (business_name, owner_name, email, phone, fssai_number, gstin, address, city, password) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)',
        (business_name, owner_name, email, phone, fssai_number, gstin, address, city, hashed)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Donor registered successfully.')


@app.route('/api/donor/login', methods=['POST'])
def donor_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, business_name, password FROM donors WHERE email = %s', (email,))
    donor = cursor.fetchone()
    cursor.close(); conn.close()

    if donor and check_password_hash(donor['password'], password):
        session.clear()
        session['donor_id'] = donor['id']
        session['donor_name'] = donor['business_name']
        return jsonify(message='Logged in.')

    return jsonify(error='Invalid email or password.'), 401


# ===========================================================
# RECEIVER: register / login
# ===========================================================
@app.route('/api/receiver/register', methods=['POST'])
def receiver_register():
    data = request.get_json(silent=True) or {}
    organization_name = (data.get('organization_name') or '').strip()
    contact_person = (data.get('contact_person') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    ngo_id = (data.get('ngo_id') or '').strip()
    address = (data.get('address') or '').strip()
    city = (data.get('city') or '').strip()
    password = data.get('password') or ''
    confirm = data.get('confirm_password') or ''

    if not all([organization_name, contact_person, email, phone, ngo_id, address, city, password]):
        return jsonify(error='Please fill in all required fields.'), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify(error='Please enter a valid email address.'), 400
    if not PHONE_PATTERN.match(phone):
        return jsonify(error='Please enter a valid 10-digit phone number.'), 400
    if len(password) < 6 or password != confirm:
        return jsonify(error='Passwords must match and be at least 6 characters.'), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id FROM receivers WHERE email = %s', (email,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify(error='That email is already registered.'), 400

    hashed = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO receivers (organization_name, contact_person, email, phone, ngo_id, address, city, password) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        (organization_name, contact_person, email, phone, ngo_id, address, city, hashed)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Receiver registered successfully.')


@app.route('/api/receiver/login', methods=['POST'])
def receiver_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, organization_name, password FROM receivers WHERE email = %s', (email,))
    receiver = cursor.fetchone()
    cursor.close(); conn.close()

    if receiver and check_password_hash(receiver['password'], password):
        session.clear()
        session['receiver_id'] = receiver['id']
        session['receiver_name'] = receiver['organization_name']
        return jsonify(message='Logged in.')

    return jsonify(error='Invalid email or password.'), 401


# ===========================================================
# VOLUNTEER: register / login
# ===========================================================
@app.route('/api/volunteer/register', methods=['POST'])
def volunteer_register():
    data = request.get_json(silent=True) or {}
    full_name = (data.get('full_name') or '').strip()
    email = (data.get('email') or '').strip()
    phone = (data.get('phone') or '').strip()
    city = (data.get('city') or '').strip()
    vehicle_type = (data.get('vehicle_type') or '').strip()
    password = data.get('password') or ''
    confirm = data.get('confirm_password') or ''

    if not all([full_name, email, phone, city, vehicle_type, password]):
        return jsonify(error='Please fill in all required fields.'), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify(error='Please enter a valid email address.'), 400
    if not PHONE_PATTERN.match(phone):
        return jsonify(error='Please enter a valid 10-digit phone number.'), 400
    if len(password) < 6 or password != confirm:
        return jsonify(error='Passwords must match and be at least 6 characters.'), 400

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id FROM volunteers WHERE email = %s', (email,))
    if cursor.fetchone():
        cursor.close(); conn.close()
        return jsonify(error='That email is already registered.'), 400

    hashed = generate_password_hash(password)
    cursor.execute(
        'INSERT INTO volunteers (full_name, email, phone, city, vehicle_type, password) '
        'VALUES (%s, %s, %s, %s, %s, %s)',
        (full_name, email, phone, city, vehicle_type, hashed)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Volunteer registered successfully.')


@app.route('/api/volunteer/login', methods=['POST'])
def volunteer_login():
    data = request.get_json(silent=True) or {}
    email = (data.get('email') or '').strip()
    password = data.get('password') or ''

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, full_name, password FROM volunteers WHERE email = %s', (email,))
    volunteer = cursor.fetchone()
    cursor.close(); conn.close()

    if volunteer and check_password_hash(volunteer['password'], password):
        session.clear()
        session['volunteer_id'] = volunteer['id']
        session['volunteer_name'] = volunteer['full_name']
        return jsonify(message='Logged in.')

    return jsonify(error='Invalid email or password.'), 401


@app.route('/api/predict/people-fed', methods=['POST'])
def predict_people_fed_route():
    data = request.get_json(silent=True) or {}
    quantity = data.get('quantity')
    unit = (data.get('unit') or '').strip()
    category = (data.get('category') or '').strip()
    food_type = (data.get('food_type') or '').strip()

    if not quantity or not unit or not category or not food_type:
        return jsonify(error='quantity, unit, category and food_type are all required.'), 400

    prediction = predict_people_fed(quantity, unit, category, food_type)
    if prediction is None:
        return jsonify(error='Prediction model is not available.'), 500

    return jsonify(estimatedPeopleFed=prediction)


# ===========================================================
# DONOR: stats, donate, history
# ===========================================================
@app.route('/api/donor/stats')
def donor_stats():
    donor_id = session.get('donor_id')
    if not donor_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) AS c FROM donations WHERE donor_id = %s', (donor_id,))
    total = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) AS c FROM donations WHERE donor_id = %s AND status = "pending"', (donor_id,))
    pending = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) AS c FROM donations WHERE donor_id = %s AND status = "completed"', (donor_id,))
    completed = cursor.fetchone()['c']
    cursor.execute('SELECT COALESCE(SUM(quantity), 0) AS s FROM donations WHERE donor_id = %s', (donor_id,))
    food_donated = cursor.fetchone()['s']
    cursor.execute('SELECT COALESCE(SUM(estimated_people_fed), 0) AS s FROM donations WHERE donor_id = %s', (donor_id,))
    people_fed = cursor.fetchone()['s']
    cursor.close(); conn.close()

    return jsonify(total=total, pending=pending, completed=completed, foodDonated=float(food_donated), peopleFed=int(people_fed))


@app.route('/api/donations', methods=['POST'])
def submit_donation():
    donor_id = session.get('donor_id')
    if not donor_id:
        return jsonify(error='Please log in.'), 401

    data = request.get_json(silent=True) or {}
    food_name = (data.get('food_name') or '').strip()
    category = (data.get('category') or '').strip()
    quantity = data.get('quantity')
    unit = (data.get('unit') or '').strip()
    preparation_date = (data.get('preparation_date') or '').strip()
    best_before = (data.get('best_before') or '').strip()
    pickup_address = (data.get('pickup_address') or '').strip()
    description = (data.get('description') or '').strip()
    food_type = (data.get('food_type') or '').strip()
    contact_number = (data.get('contact_number') or '').strip()

    if not all([food_name, category, quantity, unit, preparation_date, best_before, pickup_address, food_type, contact_number]):
        return jsonify(error='Please fill in all required fields.'), 400
    if food_type not in ('veg', 'nonveg'):
        return jsonify(error='Invalid food type.'), 400

    estimated_people_fed = predict_people_fed(quantity, unit, category, food_type)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO donations (donor_id, food_name, category, quantity, unit, preparation_date, best_before, '
        'pickup_address, description, food_type, contact_number, estimated_people_fed, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, "pending")',
        (donor_id, food_name, category, quantity, unit, preparation_date, best_before,
         pickup_address, description, food_type, contact_number, estimated_people_fed)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Donation submitted.', estimatedPeopleFed=estimated_people_fed)


@app.route('/api/donor/donations')
def donor_donations():
    donor_id = session.get('donor_id')
    if not donor_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT food_name, category, quantity, unit, best_before, status, estimated_people_fed FROM donations '
        'WHERE donor_id = %s ORDER BY created_at DESC', (donor_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


# ===========================================================
# RECEIVER: stats, available food, request, history
# ===========================================================
@app.route('/api/receiver/stats')
def receiver_stats():
    receiver_id = session.get('receiver_id')
    if not receiver_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) AS c FROM donations WHERE status = "pending"')
    available = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) AS c FROM food_requests WHERE receiver_id = %s AND status = "pending"', (receiver_id,))
    requested = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) AS c FROM food_requests WHERE receiver_id = %s AND status = "completed"', (receiver_id,))
    received = cursor.fetchone()['c']
    cursor.close(); conn.close()

    return jsonify(available=available, requested=requested, received=received)


@app.route('/api/donations/available')
def donations_available():
    if not session.get('receiver_id'):
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT d.id, d.food_name, d.quantity, d.unit, d.best_before, d.pickup_address, '
        'd.description, d.food_type, d.estimated_people_fed, dn.business_name AS donor '
        'FROM donations d JOIN donors dn ON dn.id = d.donor_id '
        'WHERE d.status = "pending" ORDER BY d.created_at DESC'
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


@app.route('/api/donations/<int:donation_id>/request', methods=['POST'])
def request_food(donation_id):
    receiver_id = session.get('receiver_id')
    if not receiver_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)

    cursor.execute('SELECT id, pickup_address, status FROM donations WHERE id = %s', (donation_id,))
    donation = cursor.fetchone()
    if not donation or donation['status'] != 'pending':
        cursor.close(); conn.close()
        return jsonify(error='That donation is no longer available.'), 400

    cursor.execute('SELECT address FROM receivers WHERE id = %s', (receiver_id,))
    receiver = cursor.fetchone()

    cursor.execute(
        'INSERT INTO food_requests (donation_id, receiver_id, status) VALUES (%s, %s, "pending")',
        (donation_id, receiver_id)
    )
    cursor.execute('UPDATE donations SET status = "requested" WHERE id = %s', (donation_id,))
    cursor.execute(
        'INSERT INTO deliveries (donation_id, receiver_id, pickup_location, delivery_location, status) '
        'VALUES (%s, %s, %s, %s, "available")',
        (donation_id, receiver_id, donation['pickup_address'], receiver['address'])
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Food requested.')


@app.route('/api/receiver/requests')
def receiver_requests():
    receiver_id = session.get('receiver_id')
    if not receiver_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT d.food_name, dn.business_name AS donor, d.quantity, d.unit, d.pickup_address, d.estimated_people_fed, fr.status '
        'FROM food_requests fr '
        'JOIN donations d ON d.id = fr.donation_id '
        'JOIN donors dn ON dn.id = d.donor_id '
        'WHERE fr.receiver_id = %s ORDER BY fr.requested_at DESC', (receiver_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


# ===========================================================
# VOLUNTEER: stats, available deliveries, accept, history
# ===========================================================
@app.route('/api/volunteer/stats')
def volunteer_stats():
    volunteer_id = session.get('volunteer_id')
    if not volunteer_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT COUNT(*) AS c FROM deliveries WHERE status = "available"')
    available = cursor.fetchone()['c']
    cursor.execute(
        'SELECT COUNT(*) AS c FROM deliveries WHERE volunteer_id = %s AND status IN ("accepted","pickedup")',
        (volunteer_id,)
    )
    active = cursor.fetchone()['c']
    cursor.execute('SELECT COUNT(*) AS c FROM deliveries WHERE volunteer_id = %s AND status = "delivered"', (volunteer_id,))
    completed = cursor.fetchone()['c']
    cursor.close(); conn.close()

    return jsonify(available=available, active=active, completed=completed)


@app.route('/api/deliveries/available')
def deliveries_available():
    if not session.get('volunteer_id'):
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT dl.id, d.food_name, dl.pickup_location, dl.delivery_location, d.quantity, d.unit, '
        'd.best_before AS pickup_time '
        'FROM deliveries dl JOIN donations d ON d.id = dl.donation_id '
        'WHERE dl.status = "available" ORDER BY dl.id DESC'
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


@app.route('/api/deliveries/<int:delivery_id>/accept', methods=['POST'])
def accept_delivery(delivery_id):
    volunteer_id = session.get('volunteer_id')
    if not volunteer_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT id, status FROM deliveries WHERE id = %s', (delivery_id,))
    delivery = cursor.fetchone()
    if not delivery or delivery['status'] != 'available':
        cursor.close(); conn.close()
        return jsonify(error='That delivery is no longer available.'), 400

    cursor.execute(
        'UPDATE deliveries SET volunteer_id = %s, status = "accepted", accepted_at = NOW() WHERE id = %s',
        (volunteer_id, delivery_id)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Delivery accepted.')


@app.route('/api/volunteer/deliveries')
def volunteer_deliveries():
    volunteer_id = session.get('volunteer_id')
    if not volunteer_id:
        return jsonify(error='Please log in.'), 401

    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute(
        'SELECT d.food_name, dl.pickup_location, dl.delivery_location, d.best_before AS pickup_time, dl.status '
        'FROM deliveries dl JOIN donations d ON d.id = dl.donation_id '
        'WHERE dl.volunteer_id = %s ORDER BY dl.accepted_at DESC', (volunteer_id,)
    )
    rows = cursor.fetchall()
    cursor.close(); conn.close()
    return jsonify(rows)


# ===========================================================
# CONTACT
# ===========================================================
@app.route('/api/contact', methods=['POST'])
def contact():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip()
    subject = (data.get('subject') or '').strip()
    message = (data.get('message') or '').strip()

    if not all([name, email, subject, message]):
        return jsonify(error='Please fill in all fields.'), 400
    if not EMAIL_PATTERN.match(email):
        return jsonify(error='Please enter a valid email address.'), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO contact_messages (name, email, subject, message) VALUES (%s, %s, %s, %s)',
        (name, email, subject, message)
    )
    conn.commit()
    cursor.close(); conn.close()
    return jsonify(message='Message sent.')


if __name__ == '__main__':
    app.run(debug=True, port=5000)
