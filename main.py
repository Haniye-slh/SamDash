from flask import Flask, redirect, render_template, request, session, url_for, flash
from flask_mail import Mail, Message
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from os import getenv
from werkzeug.utils import secure_filename
from database import db, User, Product, Order, Comment
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
app.config["SQLALCHEMY_DATABASE_URI"] = SQLALCHEMY_DATABASE_URI
app.config["SECRET_KEY"] = getenv("SECRET_KEY")

app.config["ADMIN_MAIL"] = getenv("ADMIN_MAIL")
admin_emails = [app.config["ADMIN_MAIL"]]
app.config["ADMIN_USER"] = getenv("ADMIN_USER")  
admin_usernames = [app.config["ADMIN_USER"]]

UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def override_method():
    if request.method == "POST" and request.form.get("_method") == "PATCH":
        request.environ["REQUEST_METHOD"] = "PATCH"

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

db.init_app(app)
with app.app_context():
    db.create_all()

app.jinja_env.globals['now'] = datetime.datetime.now

@app.route("/")
def home_page():
    products = Product.query.all()
    return render_template("index.html", username=session.get("username"), products=products)

@app.route("/sign-up", methods=["POST", "GET"])
def sign_up():
    global admin_emails, admin_usernames

    if request.method == "GET":
        return render_template("sign-up.html")

    elif request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password")

        if not username or not email or not password:
            return render_template("sign-up.html", error="Please fill in all fields", username=username, email=email)

        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()

        if existing_user:
            print("❌ Username already exists!")
            return render_template("sign-up.html", error="Username already exists", username=username, email=email)
        if existing_email:
            print("❌ Email already exists!")
            return render_template("sign-up.html", error="Email already exists", username=username, email=email)

        hashed_password = generate_password_hash(password, method="pbkdf2:sha256")

        role = "admin" if email in admin_emails or username in admin_usernames else "user"
        new_user = User(username=username, email=email, password=hashed_password, role=role)

        try:
            db.session.add(new_user)
            db.session.commit()
            print("✅ User successfully saved in the database!")
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error saving user: {e}")
            return render_template("sign-up.html", error="An error occurred while creating the account. Please try again.", username=username, email=email)

        saved_user = User.query.filter_by(username=username).first()
        if not saved_user:
            print("❌ User not found in DB after signup!")
            return render_template("sign-up.html", error="An unexpected error occurred. Please try again.", username=username, email=email)

        session.clear()
        session["username"] = username
        session["role"] = role
        session.modified = True

        print(f"Session username after signup: {session.get('username')}") 

        if role == "admin":
            return redirect(url_for("admin_dashboard"))
        return redirect(url_for("home_page"))

@app.route("/login", methods=["POST", "GET"])
def login():
    if request.method == "GET":
        return render_template("login.html")

    elif request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        print(f"Logging in with username: {username}")

        user = db.session.query(User).filter_by(username=username).first()

        if not user:
            print("User not found in database!")
            return render_template("login.html", error="Incorrect Username", username=username)

        if not check_password_hash(user.password, password):
            print("Incorrect password!") 
            return render_template("login.html", error="Incorrect Password", username=username)

        session["user_id"] = user.id
        session["username"] = user.username

        print("Session after login:", session.get('username'))

        session["role"] = user.role
        print(f"🔍 Checking login for username: {username}")
        user = db.session.query(User).filter_by(username=username).first()
        if not user:
            print("❌ User not found in database!")
            return render_template("login.html", error="Incorrect Username", username=username)
        else:
            print(f"✅ User found: {user.username}, Hashed Password: {user.password}")
        
        print(f"🔐 Session before setting: {session.get('username')}")
        session["username"] = user.username
        print(f"✅ Session after login: {session.get('username')}")

        print(f"User {user.username} logged in successfully!")

        if user.role == "admin":
            return redirect(url_for("admin_dashboard"))

        return redirect(url_for("home_page"))

@app.route("/logout")
def logout():
    session.pop("username", None)
    session.pop("role", None)
    session.clear()
    print("✅ User logged out, session cleared.")
    return redirect(url_for("login"))

@app.route("/admin/product-control", methods= {"GET", "POST"})
def admin_dashboard():
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    if request.method == "POST":
        name = request.form.get("productName")
        image = request.files.get("productImage")
        price = request.form.get("productPrice")
        stock = request.form.get("productStock")

        if not name or not price or not stock:
            return render_template("admin.html", error="Please fill all fields", products=Product.query.all())

        if image and allowed_file(image.filename):
            filename = secure_filename(image.filename)
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename).replace("\\", "/")
            image.save(image_path)
        else:
            image_path = None

        new_product = Product(name=name, price=float(price), stock=int(stock), image=filename)

        db.session.add(new_product)
        db.session.commit()

        return redirect(url_for("admin_dashboard"))

    products = Product.query.all()
    return render_template("admin.html", products=products)
   
@app.route("/product/<int:product_id>", methods=["GET", "POST"])
def product(product_id):
    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        comment_text = request.form.get("comment", "").strip()
        username = session.get("username")

        if not username:
            flash("You must be logged in to comment.", "warning")
            return redirect(url_for("login"))

        if not comment_text:
            flash("Comment cannot be empty.", "danger")
            return redirect(url_for("product", product_id=product_id))

        new_comment = Comment(username=username, comment=comment_text, product_id=product_id)
        db.session.add(new_comment)
        db.session.commit()
        flash("Your comment has been posted!", "success")

        return redirect(url_for("product", product_id=product_id))

    comments = Comment.query.filter_by(product_id=product_id).all()
    return render_template("product.html", product=product, comments=comments)

@app.route("/admin/orders", methods=["GET", "POST"])
def orders():
    if "username" not in session or session["username"] not in admin_usernames:
        return redirect(url_for("login"))

    if request.method == "POST":
        order_id = request.form.get("order_id")
        order = Order.query.get(order_id)
        if order:
            order.status = "Completed"
            db.session.commit()

    orders = Order.query.all()
    return render_template("admin_orders.html", orders=orders)

@app.route("/order", methods=["GET", "POST"])
def order():
    if request.method == "POST":
        product_id = request.form.get("product_id")
        address = request.form.get("address")
        quantity = int(request.form.get("quantity"))
        user = session.get("username")

        if not user:
            return redirect(url_for("login"))

        product = Product.query.get_or_404(product_id)

        if product.stock < quantity:
            flash("Out of stock!", "danger")
            return redirect(url_for("product", product_id=product.id))

        new_order = Order(username=user, product_id=product.id, address=address, quantity=quantity)
        db.session.add(new_order)

        product.stock -= quantity
        db.session.commit()

        flash("Your order has been placed successfully!", "success")
        return redirect(url_for("product", product_id=product.id))

@app.route("/product/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    product = Product.query.get_or_404(product_id)
    Order.query.filter_by(product_id=product.id).delete()

    db.session.delete(product)
    db.session.commit()

    flash("Product deleted successfully!", "success")
    return redirect(url_for("admin_dashboard"))

@app.route("/product/edit/<int:product_id>", methods=["GET", "POST"])
def edit_product(product_id):
    if "role" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    product = Product.query.get_or_404(product_id)

    if request.method == "POST":
        product.name = request.form.get("name", product.name)
        product.price = float(request.form.get("price", product.price))
        product.stock = int(request.form.get("stock", product.stock))
        
        if "image" in request.files:
            image = request.files["image"]
            if image.filename:
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                image.save(image_path)
                product.image = filename
        db.session.commit()
        flash("Product updated successfully!", "success")
        return redirect(url_for("edit_product", product_id=product.id))

    return render_template("edit_product.html", product=product)

@app.route("/payment", methods=["POST"])
def payment():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity", 1))
    address = request.form.get("address")

    product = Product.query.get_or_404(product_id)
    return render_template("payment.html", product=product, quantity=quantity, address=address)

@app.route("/confirm_payment", methods=["POST"])
def confirm_payment():
    product_id = request.form.get("product_id")
    quantity = int(request.form.get("quantity"))
    address = request.form.get("address")
    card_number = request.form.get("card_number").replace("-", "")  # حذف "-"
    cvv = request.form.get("cvv")
    expiry_date = request.form.get("expiry_date")

    user = session.get("username")
    if not user:
        return redirect(url_for("login"))

    product = Product.query.get_or_404(product_id)

    if product.stock < quantity:
        flash("Out of stock!", "danger")
        return redirect(url_for("product", product_id=product_id))

    if len(card_number) != 16 or not card_number.isdigit():
        flash("Your card was rejected!", "danger")
        return redirect(url_for("product", product_id=product_id))  # اصلاح شد

    if not expiry_date or len(expiry_date) != 5:
        flash("Invalid expiry date!", "danger")
        return redirect(url_for("product", product_id=product_id))

    new_order = Order(username=user, product_id=product.id, address=address, quantity=quantity)
    db.session.add(new_order)
    product.stock -= quantity
    db.session.commit()

    flash("Success!")
    return redirect(url_for("product", product_id=product.id))


@app.route("/my-orders")
def my_orders():
    if "username" not in session:
        flash("You must be logged in to view your orders.", "warning")
        return redirect(url_for("login"))

    user_orders = Order.query.filter_by(username=session["username"]).all()

    return render_template("my_orders.html", orders=user_orders)

app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = app.config['MAIL_USERNAME']

mail = Mail(app)

@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "GET":
        return render_template("contact.html")

    email = request.form.get("your_email", "").strip()
    message = request.form.get("your_message", "").strip()

    if not email or not message:
        flash("Error: All fields are required!", "danger")
        return redirect(url_for("contact"))

    whole_msg = f"MESSAGE: {message}\nEMAIL: {email}"
    msg = Message(subject="New Contact Form Submission", 
                  sender=app.config['MAIL_DEFAULT_SENDER'],
                  recipients=["logicwiz98@yahoo.com"])
    msg.body = whole_msg

    try:
        mail.send(msg)
        flash("Email sent successfully!", "success")
    except Exception as e:
        flash(f"Error sending email: {e}", "danger")

    return redirect(url_for("contact"))
    
@app.route("/about")
def about():
    return render_template("about.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))