from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "education_ecommerce_secret_key"

DATABASE = "database.db"


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendor_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            category TEXT,
            price REAL NOT NULL,
            image TEXT,
            status TEXT DEFAULT 'Pending',
            rating REAL DEFAULT 4.5,
            FOREIGN KEY(vendor_id) REFERENCES users(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS cart (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total REAL NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    # Default admin
    admin = conn.execute(
        "SELECT * FROM users WHERE email=?",
        ("admin@edu.com",)
    ).fetchone()

    if not admin:
        conn.execute(
            "INSERT INTO users (name,email,password,role) VALUES (?,?,?,?)",
            (
                "Administrator",
                "admin@edu.com",
                generate_password_hash("admin123"),
                "admin"
            )
        )

    conn.commit()
    conn.close()


# ---------------- HOME ----------------

@app.route("/")
def index():
    conn = get_db()

    products = conn.execute("""
        SELECT * FROM products
        WHERE status='Approved'
        ORDER BY id DESC
        LIMIT 8
    """).fetchall()

    conn.close()

    return render_template("index.html", products=products)


# ---------------- REGISTER ----------------

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]
        role = request.form["role"]

        if role not in ["user", "vendor"]:
            flash("Invalid role")
            return redirect(url_for("register"))

        conn = get_db()

        try:
            conn.execute("""
                INSERT INTO users(name,email,password,role)
                VALUES(?,?,?,?)
            """, (
                name,
                email,
                generate_password_hash(password),
                role
            ))

            conn.commit()

            flash("Registration successful! Please login.")

        except sqlite3.IntegrityError:
            flash("Email already exists.")

        conn.close()

        return redirect(url_for("login"))

    return render_template("register.html")


# ---------------- LOGIN ----------------

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        conn = get_db()

        user = conn.execute(
            "SELECT * FROM users WHERE email=?",
            (email,)
        ).fetchone()

        conn.close()

        if user and check_password_hash(user["password"], password):

            session["user_id"] = user["id"]
            session["name"] = user["name"]
            session["role"] = user["role"]

            if user["role"] == "admin":
                return redirect(url_for("admin_dashboard"))

            elif user["role"] == "vendor":
                return redirect(url_for("vendor_dashboard"))

            else:
                return redirect(url_for("index"))

        flash("Invalid email or password.")

    return render_template("login.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():

    session.clear()

    return redirect(url_for("index"))


# ---------------- PRODUCTS ----------------

@app.route("/products")
def products():

    category = request.args.get("category", "")
    search = request.args.get("search", "")

    conn = get_db()

    query = """
        SELECT * FROM products
        WHERE status='Approved'
    """

    params = []

    if category:
        query += " AND category=?"
        params.append(category)

    if search:
        query += " AND name LIKE ?"
        params.append("%" + search + "%")

    query += " ORDER BY id DESC"

    products = conn.execute(query, params).fetchall()

    conn.close()

    return render_template(
        "products.html",
        products=products
    )


# ---------------- CART ----------------

@app.route("/add_to_cart/<int:product_id>")
def add_to_cart(product_id):

    if "user_id" not in session or session["role"] != "user":
        flash("Please login as a user.")
        return redirect(url_for("login"))

    conn = get_db()

    existing = conn.execute("""
        SELECT * FROM cart
        WHERE user_id=? AND product_id=?
    """, (
        session["user_id"],
        product_id
    )).fetchone()

    if existing:

        conn.execute("""
            UPDATE cart
            SET quantity=quantity+1
            WHERE id=?
        """, (existing["id"],))

    else:

        conn.execute("""
            INSERT INTO cart(user_id,product_id,quantity)
            VALUES(?,?,1)
        """, (
            session["user_id"],
            product_id
        ))

    conn.commit()
    conn.close()

    flash("Product added to cart!")

    return redirect(url_for("products"))


@app.route("/cart")
def cart():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    items = conn.execute("""
        SELECT cart.id,
               cart.quantity,
               products.name,
               products.price,
               products.image,
               products.id AS product_id,
               cart.quantity * products.price AS subtotal
        FROM cart
        JOIN products
        ON cart.product_id = products.id
        WHERE cart.user_id=?
    """, (session["user_id"],)).fetchall()

    total = sum(item["subtotal"] for item in items)

    conn.close()

    return render_template(
        "cart.html",
        items=items,
        total=total
    )


@app.route("/remove_cart/<int:cart_id>")
def remove_cart(cart_id):

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        DELETE FROM cart
        WHERE id=? AND user_id=?
    """, (
        cart_id,
        session["user_id"]
    ))

    conn.commit()
    conn.close()

    return redirect(url_for("cart"))


# ---------------- CHECKOUT ----------------

@app.route("/checkout")
def checkout():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    items = conn.execute("""
        SELECT cart.product_id,
               cart.quantity,
               products.price
        FROM cart
        JOIN products
        ON cart.product_id=products.id
        WHERE cart.user_id=?
    """, (session["user_id"],)).fetchall()

    for item in items:

        total = item["price"] * item["quantity"]

        conn.execute("""
            INSERT INTO orders
            (user_id,product_id,quantity,total)
            VALUES(?,?,?,?)
        """, (
            session["user_id"],
            item["product_id"],
            item["quantity"],
            total
        ))

    conn.execute("""
        DELETE FROM cart
        WHERE user_id=?
    """, (session["user_id"],))

    conn.commit()
    conn.close()

    flash("Order placed successfully!")

    return redirect(url_for("orders"))


# ---------------- ORDERS ----------------

@app.route("/orders")
def orders():

    if "user_id" not in session:
        return redirect(url_for("login"))

    conn = get_db()

    orders = conn.execute("""
        SELECT orders.*,
               products.name,
               products.image
        FROM orders
        JOIN products
        ON orders.product_id=products.id
        WHERE orders.user_id=?
        ORDER BY orders.id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "orders.html",
        orders=orders
    )


# ---------------- VENDOR DASHBOARD ----------------

@app.route("/vendor")
def vendor_dashboard():

    if "user_id" not in session or session["role"] != "vendor":
        return redirect(url_for("login"))

    conn = get_db()

    products = conn.execute("""
        SELECT * FROM products
        WHERE vendor_id=?
        ORDER BY id DESC
    """, (session["user_id"],)).fetchall()

    conn.close()

    return render_template(
        "vendor_dashboard.html",
        products=products
    )


@app.route("/vendor/add", methods=["GET", "POST"])
def vendor_add():

    if "user_id" not in session or session["role"] != "vendor":
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form["name"]
        description = request.form["description"]
        category = request.form["category"]
        price = request.form["price"]
        image = request.form["image"]

        conn = get_db()

        conn.execute("""
            INSERT INTO products
            (vendor_id,name,description,category,price,image,status)
            VALUES(?,?,?,?,?,?,?)
        """, (
            session["user_id"],
            name,
            description,
            category,
            price,
            image,
            "Pending"
        ))

        conn.commit()
        conn.close()

        flash("Product submitted for admin approval.")

        return redirect(url_for("vendor_dashboard"))

    return render_template("vendor_add.html")


# ---------------- ADMIN DASHBOARD ----------------

@app.route("/admin")
def admin_dashboard():

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db()

    products = conn.execute("""
        SELECT products.*,
               users.name AS vendor_name
        FROM products
        JOIN users
        ON products.vendor_id=users.id
        ORDER BY products.id DESC
    """).fetchall()

    users = conn.execute("""
        SELECT * FROM users
        WHERE role != 'admin'
    """).fetchall()

    pending_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE status='Pending'
    """).fetchone()["count"]

    approved_count = conn.execute("""
        SELECT COUNT(*) AS count
        FROM products
        WHERE status='Approved'
    """).fetchone()["count"]

    conn.close()

    return render_template(
        "admin_dashboard.html",
        products=products,
        users=users,
        pending_count=pending_count,
        approved_count=approved_count
    )


@app.route("/admin/approve/<int:product_id>")
def approve_product(product_id):

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        UPDATE products
        SET status='Approved'
        WHERE id=?
    """, (product_id,))

    conn.commit()
    conn.close()

    flash("Product approved!")

    return redirect(url_for("admin_dashboard"))


@app.route("/admin/reject/<int:product_id>")
def reject_product(product_id):

    if "user_id" not in session or session["role"] != "admin":
        return redirect(url_for("login"))

    conn = get_db()

    conn.execute("""
        UPDATE products
        SET status='Rejected'
        WHERE id=?
    """, (product_id,))

    conn.commit()
    conn.close()

    flash("Product rejected.")

    return redirect(url_for("admin_dashboard"))

@app.route("/seed")
def seed():

    conn = get_db()

    vendor = conn.execute(
        "SELECT id FROM users WHERE role='vendor' LIMIT 1"
    ).fetchone()

    if not vendor:

        conn.execute("""
            INSERT INTO users(name,email,password,role)
            VALUES(?,?,?,?)
        """, (
            "Demo Educator",
            "vendor@edu.com",
            generate_password_hash("vendor123"),
            "vendor"
        ))

        conn.commit()

        vendor = conn.execute(
            "SELECT id FROM users WHERE email=?",
            ("vendor@edu.com",)
        ).fetchone()

    products = [

        (
            "Python Programming Masterclass",
            "Complete Python course for beginners.",
            "Programming",
            499,
            "https://images.unsplash.com/photo-1515879218367-8466d910aaa4",
            "Approved"
        ),

        (
            "Mathematics for Engineers",
            "Engineering mathematics study material.",
            "Mathematics",
            299,
            "https://images.unsplash.com/photo-1635070041078-e363dbe005cb",
            "Approved"
        ),

        (
            "Complete Science Notes",
            "Easy-to-understand science notes.",
            "Science",
            199,
            "https://images.unsplash.com/photo-1532094349884-543bc11b234d",
            "Approved"
        ),

        (
            "English Communication Course",
            "Improve your English communication skills.",
            "Languages",
            399,
            "https://images.unsplash.com/photo-1457369804613-52c61a468e7d",
            "Approved"
        )

    ]

    for product in products:

        exists = conn.execute(
            "SELECT id FROM products WHERE name=?",
            (product[0],)
        ).fetchone()

        if not exists:

            conn.execute("""
                INSERT INTO products
                (vendor_id,name,description,category,
                 price,image,status)
                VALUES(?,?,?,?,?,?,?)
            """, (
                vendor["id"],
                product[0],
                product[1],
                product[2],
                product[3],
                product[4],
                product[5]
            ))

    conn.commit()
    conn.close()

    return "Sample products added successfully!"


# ---------------- START ----------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)