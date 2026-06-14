from flask import Flask, request, jsonify, session, send_from_directory
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import os
import secrets
from datetime import datetime

from database import execute_query
from config import Config

app = Flask(__name__, static_folder='../frontend', static_url_path='')
app.config.from_object(Config)
CORS(app, supports_credentials=True)

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return jsonify({'error': 'Authentication required'}), 401
            if session.get('role') not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            return f(*args, **kwargs)
        return decorated
    return decorator

def generate_rider_id():
  return f"ADR-{secrets.token_hex(3).upper()}"

# ─── Static Pages ───────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

# ─── Auth Routes ────────────────────────────────────────────

@app.route('/api/auth/register', methods=['POST'])
def register():
    data = request.get_json()
    required = ['full_name', 'email', 'phone', 'password']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'All fields are required'}), 400

    existing = execute_query(
        "SELECT id FROM users WHERE email = %s", (data['email'],), fetch_one=True
    )
    if existing:
        return jsonify({'error': 'Email already registered'}), 409

    password_hash = generate_password_hash(data['password'])
    role = data.get('role', 'user')
    if role not in ('user', 'rider'):
        role = 'user'

    user_id = execute_query(
        "INSERT INTO users (full_name, email, phone, password_hash, role) VALUES (%s, %s, %s, %s, %s)",
        (data['full_name'], data['email'], data['phone'], password_hash, role)
    )

    if role == 'rider':
        rider_fields = ['license_number', 'motorcycle_plate', 'motorcycle_model', 'id_card_number']
        if not all(data.get(f) for f in rider_fields):
            return jsonify({'error': 'Rider registration requires license, plate, model, and ID card number'}), 400

        rider_id_number = generate_rider_id()
        execute_query(
            """INSERT INTO riders (user_id, rider_id_number, license_number, motorcycle_plate,
               motorcycle_model, motorcycle_color, id_card_number, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')""",
            (user_id, rider_id_number, data['license_number'], data['motorcycle_plate'],
             data['motorcycle_model'], data.get('motorcycle_color', ''), data['id_card_number'])
        )

    return jsonify({'message': 'Registration successful', 'user_id': user_id}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data.get('email') or not data.get('password'):
        return jsonify({'error': 'Email and password required'}), 400

    user = execute_query(
        "SELECT * FROM users WHERE email = %s", (data['email'],), fetch_one=True
    )
    if not user or not check_password_hash(user['password_hash'], data['password']):
        return jsonify({'error': 'Invalid email or password'}), 401

    session['user_id'] = user['id']
    session['role'] = user['role']
    session['full_name'] = user['full_name']

    rider_info = None
    if user['role'] == 'rider':
        rider_info = execute_query(
            "SELECT * FROM riders WHERE user_id = %s", (user['id'],), fetch_one=True
        )

    return jsonify({
        'message': 'Login successful',
        'user': {
            'id': user['id'],
            'full_name': user['full_name'],
            'email': user['email'],
            'phone': user['phone'],
            'role': user['role'],
            'rider': rider_info
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/me', methods=['GET'])
@login_required
def get_current_user():
    user = execute_query(
        "SELECT id, full_name, email, phone, role, created_at FROM users WHERE id = %s",
        (session['user_id'],), fetch_one=True
    )
    if not user:
        return jsonify({'error': 'User not found'}), 404

    rider_info = None
    if user['role'] == 'rider':
        rider_info = execute_query(
            "SELECT * FROM riders WHERE user_id = %s", (user['id'],), fetch_one=True
        )

    return jsonify({'user': {**user, 'rider': rider_info}})

# ─── Rider Routes ───────────────────────────────────────────

@app.route('/api/riders/available', methods=['GET'])
def get_available_riders():
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)

    riders = execute_query("""
        SELECT r.id, r.rider_id_number, r.motorcycle_plate, r.motorcycle_model,
               r.motorcycle_color, r.rating, r.total_rides, u.full_name, u.phone,
               rl.latitude, rl.longitude, rl.location_name, rl.updated_at
        FROM riders r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN rider_locations rl ON r.id = rl.rider_id
        WHERE r.status = 'approved' AND r.is_available = TRUE
    """, fetch=True) or []

    if lat and lng:
        for rider in riders:
            if rider.get('latitude') and rider.get('longitude'):
                rider['distance'] = round(haversine(lat, lng, float(rider['latitude']), float(rider['longitude'])), 2)
            else:
                rider['distance'] = None
        riders.sort(key=lambda x: x.get('distance') or 999)

    return jsonify({'riders': riders})

@app.route('/api/riders/<int:rider_id>', methods=['GET'])
def get_rider(rider_id):
    rider = execute_query("""
        SELECT r.id, r.rider_id_number, r.motorcycle_plate, r.motorcycle_model,
               r.motorcycle_color, r.rating, r.total_rides, r.status, r.is_available,
               u.full_name, u.phone, rl.latitude, rl.longitude, rl.location_name
        FROM riders r
        JOIN users u ON r.user_id = u.id
        LEFT JOIN rider_locations rl ON r.id = rl.rider_id
        WHERE r.id = %s
    """, (rider_id,), fetch_one=True)

    if not rider:
        return jsonify({'error': 'Rider not found'}), 404
    return jsonify({'rider': rider})

@app.route('/api/riders/availability', methods=['PUT'])
@role_required('rider')
def toggle_availability():
    rider = execute_query(
        "SELECT id, is_available, status FROM riders WHERE user_id = %s",
        (session['user_id'],), fetch_one=True
    )
    if not rider:
        return jsonify({'error': 'Rider profile not found'}), 404
    if rider.get('status') != 'approved':
        return jsonify({'error': 'Your account is pending approval'}), 403

    new_status = not rider['is_available']
    execute_query(
        "UPDATE riders SET is_available = %s WHERE id = %s",
        (new_status, rider['id'])
    )
    return jsonify({'is_available': new_status, 'message': f"Now {'available' if new_status else 'unavailable'}"})

@app.route('/api/riders/location', methods=['PUT'])
@role_required('rider')
def update_location():
    data = request.get_json()
    lat = data.get('latitude')
    lng = data.get('longitude')
    if lat is None or lng is None:
        return jsonify({'error': 'Latitude and longitude required'}), 400

    rider = execute_query(
        "SELECT id FROM riders WHERE user_id = %s", (session['user_id'],), fetch_one=True
    )
    if not rider:
        return jsonify({'error': 'Rider profile not found'}), 404

    existing = execute_query(
        "SELECT id FROM rider_locations WHERE rider_id = %s", (rider['id'],), fetch_one=True
    )
    if existing:
        execute_query(
            "UPDATE rider_locations SET latitude = %s, longitude = %s, location_name = %s WHERE rider_id = %s",
            (lat, lng, data.get('location_name', ''), rider['id'])
        )
    else:
        execute_query(
            "INSERT INTO rider_locations (rider_id, latitude, longitude, location_name) VALUES (%s, %s, %s, %s)",
            (rider['id'], lat, lng, data.get('location_name', ''))
        )

    return jsonify({'message': 'Location updated successfully'})

# ─── Booking Routes ─────────────────────────────────────────

@app.route('/api/bookings', methods=['POST'])
@role_required('user')
def create_booking():
    data = request.get_json()
    required = ['pickup_location', 'destination']
    if not all(data.get(f) for f in required):
        return jsonify({'error': 'Pickup and destination are required'}), 400

    booking_id = execute_query(
        """INSERT INTO bookings (user_id, rider_id, pickup_location, pickup_lat, pickup_lng,
           destination, destination_lat, destination_lng, fare, notes, status)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')""",
        (session['user_id'], data.get('rider_id'), data['pickup_location'],
         data.get('pickup_lat'), data.get('pickup_lng'), data['destination'],
         data.get('destination_lat'), data.get('destination_lng'),
         data.get('fare'), data.get('notes', ''))
    )
    return jsonify({'message': 'Ride requested successfully', 'booking_id': booking_id}), 201

@app.route('/api/bookings/my', methods=['GET'])
@login_required
def get_my_bookings():
    role = session.get('role')
    if role == 'user':
        bookings = execute_query("""
            SELECT b.*, u.full_name as rider_name, r.rider_id_number, r.motorcycle_plate
            FROM bookings b
            LEFT JOIN riders r ON b.rider_id = r.id
            LEFT JOIN users u ON r.user_id = u.id
            WHERE b.user_id = %s ORDER BY b.requested_at DESC
        """, (session['user_id'],), fetch=True)
    elif role == 'rider':
        rider = execute_query(
            "SELECT id FROM riders WHERE user_id = %s", (session['user_id'],), fetch_one=True
        )
        if not rider:
            return jsonify({'bookings': []})
        bookings = execute_query("""
            SELECT b.*, u.full_name as passenger_name, u.phone as passenger_phone
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            WHERE b.rider_id = %s OR (b.rider_id IS NULL AND b.status = 'pending')
            ORDER BY b.requested_at DESC
        """, (rider['id'],), fetch=True)
    else:
        bookings = execute_query("""
            SELECT b.*, u.full_name as passenger_name, ru.full_name as rider_name
            FROM bookings b
            JOIN users u ON b.user_id = u.id
            LEFT JOIN riders r ON b.rider_id = r.id
            LEFT JOIN users ru ON r.user_id = ru.id
            ORDER BY b.requested_at DESC LIMIT 50
        """, fetch=True)

    return jsonify({'bookings': bookings or []})

@app.route('/api/bookings/<int:booking_id>/status', methods=['PUT'])
@login_required
def update_booking_status(booking_id):
    data = request.get_json()
    new_status = data.get('status')
    valid_statuses = ['accepted', 'in_progress', 'completed', 'cancelled']
    if new_status not in valid_statuses:
        return jsonify({'error': 'Invalid status'}), 400

    booking = execute_query("SELECT * FROM bookings WHERE id = %s", (booking_id,), fetch_one=True)
    if not booking:
        return jsonify({'error': 'Booking not found'}), 404

    role = session.get('role')
    rider = None
    if role == 'rider':
        rider = execute_query(
            "SELECT id FROM riders WHERE user_id = %s", (session['user_id'],), fetch_one=True
        )

    if role == 'user' and booking['user_id'] != session['user_id']:
        return jsonify({'error': 'Not authorized'}), 403
    if role == 'rider' and new_status in ('accepted', 'in_progress', 'completed'):
        if not rider:
            return jsonify({'error': 'Rider profile not found'}), 404
        execute_query("UPDATE bookings SET rider_id = %s WHERE id = %s AND rider_id IS NULL",
                      (rider['id'], booking_id))

    extra = ""
    if new_status == 'accepted':
        extra = ", accepted_at = NOW()"
        if rider:
            execute_query("UPDATE riders SET is_available = FALSE WHERE id = %s", (rider['id'],))
    elif new_status == 'completed':
        extra = ", completed_at = NOW()"
        if booking.get('rider_id') or (rider and rider['id']):
            rid = booking.get('rider_id') or rider['id']
            execute_query("UPDATE riders SET is_available = TRUE, total_rides = total_rides + 1 WHERE id = %s", (rid,))

    execute_query(f"UPDATE bookings SET status = %s{extra} WHERE id = %s", (new_status, booking_id))
    return jsonify({'message': f'Booking {new_status}'})

# ─── Admin Routes ───────────────────────────────────────────

@app.route('/api/admin/riders', methods=['GET'])
@role_required('admin')
def admin_get_riders():
    riders = execute_query("""
        SELECT r.*, u.full_name, u.email, u.phone
        FROM riders r JOIN users u ON r.user_id = u.id
        ORDER BY r.created_at DESC
    """, fetch=True)
    return jsonify({'riders': riders or []})

@app.route('/api/admin/riders/<int:rider_id>/status', methods=['PUT'])
@role_required('admin')
def admin_update_rider_status(rider_id):
    data = request.get_json()
    status = data.get('status')
    if status not in ('approved', 'rejected', 'suspended'):
        return jsonify({'error': 'Invalid status'}), 400

    execute_query("UPDATE riders SET status = %s WHERE id = %s", (status, rider_id))
    return jsonify({'message': f'Rider status updated to {status}'})

@app.route('/api/admin/stats', methods=['GET'])
@role_required('admin')
def admin_stats():
    stats = {}
    stats['total_users'] = execute_query("SELECT COUNT(*) as count FROM users WHERE role='user'", fetch_one=True)['count']
    stats['total_riders'] = execute_query("SELECT COUNT(*) as count FROM riders", fetch_one=True)['count']
    stats['approved_riders'] = execute_query("SELECT COUNT(*) as count FROM riders WHERE status='approved'", fetch_one=True)['count']
    stats['pending_riders'] = execute_query("SELECT COUNT(*) as count FROM riders WHERE status='pending'", fetch_one=True)['count']
    stats['total_bookings'] = execute_query("SELECT COUNT(*) as count FROM bookings", fetch_one=True)['count']
    stats['active_bookings'] = execute_query(
        "SELECT COUNT(*) as count FROM bookings WHERE status IN ('pending','accepted','in_progress')", fetch_one=True
    )['count']
    stats['available_riders'] = execute_query(
        "SELECT COUNT(*) as count FROM riders WHERE is_available=TRUE AND status='approved'", fetch_one=True
    )['count']
    return jsonify({'stats': stats})

# ─── Campus Locations ───────────────────────────────────────

@app.route('/api/locations', methods=['GET'])
def get_campus_locations():
    locations = execute_query("SELECT * FROM campus_locations ORDER BY name", fetch=True)
    return jsonify({'locations': locations or []})

# ─── Helpers ────────────────────────────────────────────────

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    return R * 2 * atan2(sqrt(a), sqrt(1-a))

# ─── Init ───────────────────────────────────────────────────

@app.route('/api/init-admin', methods=['POST'])
def init_admin():
    admin = execute_query("SELECT id FROM users WHERE role='admin' LIMIT 1", fetch_one=True)
    if admin:
        execute_query(
            "UPDATE users SET password_hash = %s WHERE role = 'admin'",
            (generate_password_hash('admin123'),)
        )
    else:
        execute_query(
            "INSERT INTO users (full_name, email, phone, password_hash, role) VALUES (%s, %s, %s, %s, 'admin')",
            ('System Admin', 'admin@adustech.edu.ng', '08000000000', generate_password_hash('admin123'))
        )
    return jsonify({'message': 'Admin initialized. Email: admin@adustech.edu.ng, Password: admin123'})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
