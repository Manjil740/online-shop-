from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
import json
import os
from werkzeug.utils import secure_filename
from functools import wraps
from datetime import datetime

app = Flask(__name__)
app.secret_key = '20101201s'

# Configuration
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure directories exist
os.makedirs('data', exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize data files if they don't exist
def init_data_files():
    data_files = {
        'users.json': {
            "admin": {
                "password": "admin123",
                "balance": 1000.0,
                "history": [],
                "role": "admin",
                "admin_level": 3,  # 3 = top admin, 2 = mid admin, 1 = junior admin
                "notifications": []
            }
        },
        'items.json': [
            {
                "id": 1,
                "name": "Fidget Toy",
                "price": 25.0,
                "description": "A fun stress-relieving toy",
                "image": "default_item.jpg",
                "seller": "admin",
                "stock": 100
            }
        ],
        's.json': []
    }
    
    for filename, default_data in data_files.items():
        if not os.path.exists(f'data/{filename}'):
            with open(f'data/{filename}', 'w') as f:
                json.dump(default_data, f, indent=4)

init_data_files()

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def load_data(filename):
    with open(f'data/{filename}', 'r') as f:
        return json.load(f)

def save_data(data, filename):
    with open(f'data/{filename}', 'w') as f:
        json.dump(data, f, indent=4)

# Decorators for role-based access control
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(level=1):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'username' not in session:
                flash('Please log in to access this page.', 'danger')
                return redirect(url_for('login'))
            users = load_data('users.json')
            user = users.get(session['username'])
            if user['role'] != 'admin' or user.get('admin_level', 0) < level:
                flash('You do not have permission to access this page.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def seller_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        users = load_data('users.json')
        user = users.get(session['username'])
        if user['role'] != 'seller':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def home():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data('users.json')
        
        if username in users and users[username]['password'] == password:
            session['username'] = username
            session['role'] = users[username]['role']
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        users = load_data('users.json')
        
        if username in users:
            flash('Username already exists', 'danger')
        else:
            users[username] = {
                "password": password,
                "balance": 100.0,
                "history": [],
                "role": "buyer",
                "notifications": []
            }
            save_data(users, 'users.json')
            flash('Registration successful! Please login.', 'success')
            return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    users = load_data('users.json')
    user = users[session['username']]
    
    if user['role'] == 'admin':
        return redirect(url_for('admin_dashboard'))
    elif user['role'] == 'seller':
        return redirect(url_for('seller_dashboard'))
    else:
        return redirect(url_for('buyer_dashboard'))

# Admin routes
@app.route('/admin')
@admin_required(level=1)
def admin_dashboard():
    users = load_data('users.json')
    items = load_data('items.json')
    notifications = load_data('notifications.json')
    
    # Filter notifications for this admin
    admin_notifications = [n for n in notifications if n['type'] == 'admin' or 
                          (n['type'] == 'seller_request' and n['status'] == 'pending')]
    
    return render_template('admin.html', 
                         users=users, 
                         items=items, 
                         notifications=admin_notifications,
                         current_user=users[session['username']])

@app.route('/admin/promote_user', methods=['POST'])
@admin_required(level=2)  # Only mid and top admins can promote
def promote_user():
    username = request.form['username']
    new_role = request.form['role']
    admin_level = int(request.form.get('admin_level', 1))
    
    users = load_data('users.json')
    
    if username not in users:
        flash('User not found', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    current_user = users[session['username']]
    if current_user.get('admin_level', 0) <= admin_level:
        flash('You cannot promote to your own level or higher', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    users[username]['role'] = new_role
    if new_role == 'admin':
        users[username]['admin_level'] = admin_level
    
    save_data(users, 'users.json')
    flash(f'Successfully promoted {username} to {new_role}', 'success')
    return redirect(url_for('admin_dashboard'))

@app.route('/admin/process_notification/<int:notification_id>', methods=['POST'])
@admin_required(level=1)
def process_notification(notification_id):
    action = request.form['action']
    notifications = load_data('notifications.json')
    users = load_data('users.json')
    
    if notification_id >= len(notifications):
        flash('Invalid notification', 'danger')
        return redirect(url_for('admin_dashboard'))
    
    notification = notifications[notification_id]
    
    if action == 'approve':
        if notification['type'] == 'seller_request':
            users[notification['from']]['role'] = 'seller'
            save_data(users, 'users.json')
            notification['status'] = 'approved'
            # Notify the user
            users[notification['from']]['notifications'].append({
                'message': 'Your seller request has been approved!',
                'type': 'success'
            })
            save_data(users, 'users.json')
            flash('Seller request approved', 'success')
    
    elif action == 'reject':
        notification['status'] = 'rejected'
        if notification['type'] == 'seller_request':
            # Notify the user
            users[notification['from']]['notifications'].append({
                'message': 'Your seller request has been rejected.',
                'type': 'warning'
            })
            save_data(users, 'users.json')
            flash('Seller request rejected', 'info')
    
    save_data(notifications, 'notifications.json')
    return redirect(url_for('admin_dashboard'))

# Seller routes
@app.route('/seller')
@seller_required
def seller_dashboard():
    users = load_data('users.json')
    items = load_data('items.json')
    
    # Get items belonging to this seller
    seller_items = [item for item in items if item['seller'] == session['username']]
    
    return render_template('seller.html', 
                         items=seller_items,
                         user=users[session['username']])

@app.route('/seller/request', methods=['POST'])
@login_required
def request_seller():
    users = load_data('users.json')
    notifications = load_data('notifications.json')
    
    if users[session['username']]['role'] != 'buyer':
        flash('You are already a seller or admin', 'warning')
        return redirect(url_for('dashboard'))
    
    # Check if there's already a pending request
    for n in notifications:
        if n['type'] == 'seller_request' and n['from'] == session['username'] and n['status'] == 'pending':
            flash('You already have a pending seller request', 'info')
            return redirect(url_for('dashboard'))
    
    # Create new notification
    notifications.append({
        'type': 'seller_request',
        'from': session['username'],
        'message': f"{session['username']} wants to become a seller",
        'status': 'pending',
        'timestamp': datetime.now().isoformat()
    })
    
    save_data(notifications, 'notifications.json')
    flash('Seller request submitted. Please wait for admin approval.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/seller/add_item', methods=['GET', 'POST'])
@seller_required
def add_item():
    if request.method == 'POST':
        name = request.form['name']
        price = float(request.form['price'])
        description = request.form['description']
        stock = int(request.form['stock'])
        
        # Handle file upload
        if 'image' not in request.files:
            flash('No file part', 'danger')
            return redirect(request.url)
        
        file = request.files['image']
        if file.filename == '':
            filename = 'default_item.jpg'
        else:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            else:
                flash('Invalid file type', 'danger')
                return redirect(request.url)
        
        items = load_data('items.json')
        new_id = max([item['id'] for item in items], default=0) + 1
        
        new_item = {
            'id': new_id,
            'name': name,
            'price': price,
            'description': description,
            'image': filename,
            'seller': session['username'],
            'stock': stock
        }
        
        items.append(new_item)
        save_data(items, 'items.json')
        flash('Item added successfully!', 'success')
        return redirect(url_for('seller_dashboard'))
    
    return render_template('add_item.html')

@app.route('/seller/edit_item/<int:item_id>', methods=['GET', 'POST'])
@seller_required
def edit_item(item_id):
    items = load_data('items.json')
    item = next((i for i in items if i['id'] == item_id), None)
    
    if not item or item['seller'] != session['username']:
        flash('Item not found or you do not have permission to edit it', 'danger')
        return redirect(url_for('seller_dashboard'))
    
    if request.method == 'POST':
        item['name'] = request.form['name']
        item['price'] = float(request.form['price'])
        item['description'] = request.form['description']
        item['stock'] = int(request.form['stock'])
        
        # Handle file upload if a new image is provided
        if 'image' in request.files:
            file = request.files['image']
            if file.filename != '':
                if file and allowed_file(file.filename):
                    # Delete old image if it's not the default
                    if item['image'] != 'default_item.jpg':
                        try:
                            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], item['image']))
                        except:
                            pass
                    
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    item['image'] = filename
        
        save_data(items, 'items.json')
        flash('Item updated successfully!', 'success')
        return redirect(url_for('seller_dashboard'))
    
    return render_template('edit_item.html', item=item)

@app.route('/seller/delete_item/<int:item_id>')
@seller_required
def delete_item(item_id):
    items = load_data('items.json')
    item = next((i for i in items if i['id'] == item_id), None)
    
    if not item or item['seller'] != session['username']:
        flash('Item not found or you do not have permission to delete it', 'danger')
        return redirect(url_for('seller_dashboard'))
    
    # Remove the image if it's not the default
    if item['image'] != 'default_item.jpg':
        try:
            os.remove(os.path.join(app.config['UPLOAD_FOLDER'], item['image']))
        except:
            pass
    
    items = [i for i in items if i['id'] != item_id]
    save_data(items, 'items.json')
    flash('Item deleted successfully!', 'success')
    return redirect(url_for('seller_dashboard'))

# Buyer routes
@app.route('/buyer')
@login_required
def buyer_dashboard():
    items = load_data('items.json')
    users = load_data('users.json')
    user = users[session['username']]
    
    return render_template('buyer.html', items=items, user=user)

@app.route('/item/<int:item_id>')
@login_required
def item_detail(item_id):
    items = load_data('items.json')
    item = next((i for i in items if i['id'] == item_id), None)
    
    if not item:
        flash('Item not found', 'danger')
        return redirect(url_for('buyer_dashboard'))
    
    users = load_data('users.json')
    seller = users.get(item['seller'], {'username': 'Unknown'})
    
    return render_template('item_detail.html', item=item, seller=seller)

@app.route('/buy', methods=['POST'])
@login_required
def buy_item():
    item_id = int(request.form['item_id'])
    quantity = int(request.form.get('quantity', 1))
    
    items = load_data('items.json')
    users = load_data('users.json')
    
    item = next((i for i in items if i['id'] == item_id), None)
    if not item:
        flash('Item not found', 'danger')
        return redirect(url_for('buyer_dashboard'))
    
    if item['stock'] < quantity:
        flash('Not enough stock available', 'danger')
        return redirect(url_for('item_detail', item_id=item_id))
    
    total_price = item['price'] * quantity
    buyer = users[session['username']]
    
    if buyer['balance'] < total_price:
        flash('Insufficient funds', 'danger')
        return redirect(url_for('item_detail', item_id=item_id))
    
    # Process transaction
    buyer['balance'] -= total_price
    item['stock'] -= quantity
    
    # Add to buyer's history
    buyer['history'].append({
        'type': 'purchase',
        'item_id': item_id,
        'item_name': item['name'],
        'quantity': quantity,
        'total': total_price,
        'timestamp': datetime.now().isoformat()
    })
    
    # Add to seller's history if seller exists
    if item['seller'] in users:
        seller = users[item['seller']]
        seller['balance'] += total_price
        seller['history'].append({
            'type': 'sale',
            'item_id': item_id,
            'item_name': item['name'],
            'quantity': quantity,
            'total': total_price,
            'buyer': session['username'],
            'timestamp': datetime.now().isoformat()
        })
    
    save_data(users, 'users.json')
    save_data(items, 'items.json')
    
    flash(f'Successfully purchased {quantity} {item["name"]}(s) for ${total_price:.2f}', 'success')
    return redirect(url_for('item_detail', item_id=item_id))

@app.route('/notifications')
@login_required
def view_notifications():
    users = load_data('users.json')
    user = users[session['username']]
    
    # Mark notifications as read
    unread = [n for n in user['notifications'] if not n.get('read', False)]
    for n in user['notifications']:
        n['read'] = True
    save_data(users, 'users.json')
    
    return render_template('notifications.html', notifications=user['notifications'], unread_count=len(unread))
@app.context_processor
def inject_user():
    users = load_data('users.json')
    username = session.get('username')
    if username and username in users:
        return dict(user=users[username])
    return dict(user=None)
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M:%S'):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value  # Return as-is if it's not ISO format
    return value.strftime(format)



if __name__ == '__main__':
    app.run(debug=True)