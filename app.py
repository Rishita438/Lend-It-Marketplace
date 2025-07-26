import os
from datetime import datetime, timedelta, date
from faker import Faker
import random

from flask import Flask, render_template, request, redirect, url_for, flash, session

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, case, and_
from sqlalchemy.orm import aliased

# Configure Flask app and SQLAlchemy
app = Flask(__name__)
app.secret_key = "your_secret_key"  # change this to a random secret key

# Change the SQLALCHEMY_DATABASE_URI to point to your MySQL database if desired.
# For testing purposes, you can use SQLite by uncommenting the next line:
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lendit.db'

# Example MySQL connection (adjust username, password and host accordingly):
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Vikram1803%40@localhost/LendIT'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
fake = Faker()


#########################################
# MODELS (Mapping the given schema)
#########################################

class User(db.Model):
    __tablename__ = 'Users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    phone = db.Column(db.String(15), unique=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('renter', 'owner', 'admin'), nullable=False)

    # relationships
    products = db.relationship('Product', backref='owner', cascade="all, delete-orphan")
    rentals = db.relationship('Rental', backref='renter', cascade="all, delete-orphan")
    payments = db.relationship('Payment', backref='user', cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='user', cascade="all, delete-orphan")

class Product(db.Model):
    __tablename__ = 'Products'
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    category = db.Column(db.Enum('mens', 'womens', 'accessories'), nullable=False)
    sub_category = db.Column(db.String(255))
    owner_id = db.Column(db.Integer, db.ForeignKey('Users.user_id', ondelete='CASCADE'))
    rental_price = db.Column(db.Numeric(10, 2), nullable=False)
    available_quantity = db.Column(db.Integer, nullable=False)

    rentals = db.relationship('Rental', backref='product', cascade="all, delete-orphan")
    reviews = db.relationship('Review', backref='product', cascade="all, delete-orphan")
    maintenance = db.relationship('Maintenance', uselist=False, backref='product', cascade="all, delete-orphan")

class Rental(db.Model):
    __tablename__ = 'Rentals'
    rental_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    renter_id = db.Column(db.Integer, db.ForeignKey('Users.user_id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('Products.product_id', ondelete='CASCADE'))
    rental_start = db.Column(db.Date, nullable=False)
    rental_end = db.Column(db.Date, nullable=False)
    total_cost = db.Column(db.Numeric(10, 2), nullable=False)
    status = db.Column(db.Enum('ongoing', 'completed', 'canceled'), nullable=False)

    payment = db.relationship('Payment', backref='rental', cascade="all, delete-orphan")

class Payment(db.Model):
    __tablename__ = 'Payments'
    payment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rental_id = db.Column(db.Integer, db.ForeignKey('Rentals.rental_id', ondelete='CASCADE'))
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id', ondelete='CASCADE'))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_status = db.Column(db.Enum('pending', 'completed', 'failed'), nullable=False)
    payment_date = db.Column(db.DateTime, default=datetime.utcnow)

class Review(db.Model):
    __tablename__ = 'Reviews'
    review_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.user_id', ondelete='CASCADE'))
    product_id = db.Column(db.Integer, db.ForeignKey('Products.product_id', ondelete='CASCADE'))
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text)
    review_date = db.Column(db.DateTime, default=datetime.utcnow)

class Maintenance(db.Model):
    __tablename__ = 'Maintenance'
    maintenance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('Products.product_id', ondelete='CASCADE'))
    last_cleaned = db.Column(db.Date, nullable=False)
    next_cleaning_due = db.Column(db.Date)
    status = db.Column(db.Enum('pending', 'completed'), nullable=False)


#########################################
# UTILITY FUNCTIONS FOR DUMMY DATA
#########################################

def populate_dummy_data():
    # Only populate if no users exist
    if User.query.first():
        return

    roles = ['renter', 'owner', 'admin']
    categories = ['mens', 'womens', 'accessories']
    sub_categories = {
        'mens': ['tuxedo', 'casual', 'formal'],
        'womens': ['dress', 'casual', 'ethnic'],
        'accessories': ['watch', 'bag', 'jewelry']
    }
    status_choices = ['ongoing', 'completed', 'canceled']
    payment_status_choices = ['pending', 'completed', 'failed']
    maintenance_status_choices = ['pending', 'completed']

    users = []
    products = []
    rentals = []
    payments = []
    reviews = []
    maintenances = []

    # Create 50 Users
    for _ in range(50):
        user = User(
            name=fake.name(),
            email=fake.unique.email(),
            phone=fake.unique.phone_number()[:15],
            password=fake.password(length=10),
            role=random.choice(roles)
        )
        users.append(user)
        db.session.add(user)
    db.session.commit()

    user_ids = [user.user_id for user in User.query.all()]

    # Create 50 Products
    for _ in range(50):
        # Choose a random owner from users with role 'owner'
        owners = User.query.filter(User.role == 'owner').all()
        if owners:
            owner = random.choice(owners)
        else:
            # fallback: choose a random user
            owner = random.choice(User.query.all())
        cat = random.choice(categories)
        product = Product(
            name=fake.word().capitalize() + " " + fake.word().capitalize(),
            category=cat,
            sub_category=random.choice(sub_categories[cat]),
            owner_id=owner.user_id,
            rental_price=round(random.uniform(50, 2000), 2),
            available_quantity=random.randint(1, 10)
        )
        products.append(product)
        db.session.add(product)
    db.session.commit()

    product_ids = [product.product_id for product in Product.query.all()]

    # Create 50 Rentals
    for _ in range(50):
        renters = User.query.filter(User.role=='renter').all()
        if renters:
            renter = random.choice(renters)
        else:
            renter = random.choice(User.query.all())
        prod = random.choice(Product.query.all())
        start_date = fake.date_between(start_date='-1y', end_date='today')
        days = random.randint(1, 15)  # rental period between 1 and 15 days
        end_date = start_date + timedelta(days=days)
        rental = Rental(
            renter_id=renter.user_id,
            product_id=prod.product_id,
            rental_start=start_date,
            rental_end=end_date,
            total_cost=round(float(prod.rental_price) * days, 2),
            status=random.choice(status_choices)
        )
        rentals.append(rental)
        db.session.add(rental)
    db.session.commit()

    rental_ids = [rental.rental_id for rental in Rental.query.all()]

    # Create 50 Payments
    for _ in range(50):
        if rental_ids:
            rental_id = random.choice(rental_ids)
            rental_obj = Rental.query.get(rental_id)
            pay = Payment(
                rental_id=rental_id,
                user_id=rental_obj.renter_id,
                amount=rental_obj.total_cost,
                payment_status=random.choice(payment_status_choices),
                payment_date=datetime.utcnow()
            )
            payments.append(pay)
            db.session.add(pay)
    db.session.commit()

    # Create 50 Reviews
    for _ in range(50):
        prod = random.choice(Product.query.all())
        renter_list = Rental.query.filter_by(product_id=prod.product_id).all()
        if renter_list:
            reviewer = random.choice(renter_list).renter_id
        else:
            reviewer = random.choice(user_ids)
        review = Review(
            user_id=reviewer,
            product_id=prod.product_id,
            rating=random.randint(1, 5),
            comment=fake.sentence(),
            review_date=datetime.utcnow()
        )
        reviews.append(review)
        db.session.add(review)
    db.session.commit()

    # Create 50 Maintenance entries
    for prod in Product.query.all():
        last_cleaned = fake.date_between(start_date='-6m', end_date='today')
        maintenance = Maintenance(
            product_id=prod.product_id,
            last_cleaned=last_cleaned,
            next_cleaning_due=last_cleaned + timedelta(days=30),
            status=random.choice(maintenance_status_choices)
        )
        maintenances.append(maintenance)
        db.session.add(maintenance)
    db.session.commit()


#########################################
# SETUP BEFORE FIRST REQUEST (WORKAROUND)
#########################################

setup_done = False

@app.before_request
def setup_once():
    global setup_done
    if not setup_done:
        db.create_all()
        populate_dummy_data()
        setup_done = True


#########################################
# ROUTES AND QUERY HANDLERS
#########################################

@app.route('/')
def index():
    """
    Render a menu page with buttons/forms for all query actions.
    The mapping between the buttons and queries (see comments below) is as follows:
    
    1. Find Renters → /query_renters  
    2. Renter-Product-Owner pairs → /query_rental_pairs  
    3. Count products by user → /query_products_by_user  
    4. Count products by user with >2 products → /query_products_by_user_filtered  
    5. Buyers with total spending more than average spending → /query_buyers_above_avg  
    6. Products never rented → /query_products_not_rented  
    7. Products with avg renting duration → /query_avg_renting_duration  
    8. Top 5 products by revenue → /query_top_revenue  
    9. Products with rental price above category average → /query_products_above_avg_price  
    10. List sellers and admins → /query_sellers_admins  
    11. Role specific names → /query_role_specific  
    12. Filter mens tuxedo under 1500 → /query_filter_mens_tuxedo  
    13. Filter womens products with avg rating ≥4 and price < 1300 → /query_filter_womens_rating  
    14. Filter accessories products with qty >3 and cleaned last month → /query_filter_accessories_cleaned  
    15. Sort mens/womens products by descending avg rating → /query_sort_products_avg_rating  
    16. Users who are selling and renting with >2 products listed and spent >700 → /query_multifunction_users  
    """
    return render_template('index.html')


@app.route('/query_renters')
def query_renters():
    renters = User.query.filter_by(role='renter').with_entities(User.user_id, User.name, User.email).all()
    return render_template('results.html', title="Renters", results=renters)


@app.route('/query_rental_pairs')
def query_rental_pairs():
    renter_alias = aliased(User)
    owner_alias = aliased(User)
    pairs = db.session.query(
                Rental.rental_id,
                renter_alias.name.label("renter_name"),
                Product.name.label("product_name"),
                owner_alias.name.label("owner_name")
            ).join(renter_alias, Rental.renter_id == renter_alias.user_id
            ).join(Product, Rental.product_id == Product.product_id
            ).join(owner_alias, Product.owner_id == owner_alias.user_id).all()
    return render_template('results.html', title="Rental Pairs", results=pairs)


@app.route('/query_products_by_user')
def query_products_by_user():
    counts = db.session.query(
                User.name.label("owner_name"),
                func.count(Product.product_id).label("total_products")
            ).join(Product, Product.owner_id == User.user_id
            ).group_by(User.user_id, User.name).all()
    return render_template('results.html', title="Products Count by Owner", results=counts)


@app.route('/query_products_by_user_filtered')
def query_products_by_user_filtered():
    counts = db.session.query(
                User.name.label("owner_name"),
                func.count(Product.product_id).label("total_products")
            ).join(Product, Product.owner_id == User.user_id
            ).group_by(User.user_id, User.name
            ).having(func.count(Product.product_id) > 2).all()
    return render_template('results.html', title="Owners with >2 Products Listed", results=counts)


@app.route('/query_buyers_above_avg')
def query_buyers_above_avg():
    avg_total = db.session.query(func.avg(Rental.total_cost)).scalar()
    subq = db.session.query(
                Rental.renter_id,
                func.sum(Rental.total_cost).label('total_spent')
            ).group_by(Rental.renter_id).subquery()
    buyers = db.session.query(User.name).join(subq, User.user_id == subq.c.renter_id
                ).filter(subq.c.total_spent > avg_total).all()
    return render_template('results.html', title="Buyers with Spending > Average", results=buyers)


@app.route('/query_products_not_rented')
def query_products_not_rented():
    subq = db.session.query(Rental.product_id)
    products = Product.query.filter(~Product.product_id.in_(subq)).with_entities(Product.product_id, Product.name).all()
    return render_template('results.html', title="Products Not Rented", results=products)


@app.route('/query_avg_renting_duration')
def query_avg_renting_duration():
    durations = db.session.query(
                    Product.name.label("product_name"),
                    func.avg(func.datediff(Rental.rental_end, Rental.rental_start)).label("avg_duration")
                ).join(Rental, Rental.product_id == Product.product_id
                ).group_by(Product.product_id, Product.name).all()
    return render_template('results.html', title="Average Renting Duration", results=durations)


@app.route('/query_top_revenue')
def query_top_revenue():
    revenue = db.session.query(
                Product.name.label("product_name"),
                func.sum(Rental.total_cost).label("revenue")
            ).join(Rental, Rental.product_id == Product.product_id
            ).group_by(Product.product_id, Product.name
            ).order_by(func.sum(Rental.total_cost).desc()
            ).limit(5).all()
    return render_template('results.html', title="Top 5 Revenue Generators", results=revenue)


@app.route('/query_products_above_avg_price')
def query_products_above_avg_price():
    subq = db.session.query(
                Product.category,
                func.avg(Product.rental_price).label("avg_price")
            ).group_by(Product.category).subquery()
    products = db.session.query(Product.name, Product.category, Product.rental_price
                ).join(subq, Product.category == subq.c.category
                ).filter(Product.rental_price > subq.c.avg_price).all()
    return render_template('results.html', title="Products Above Category Average Price", results=products)


@app.route('/query_sellers_admins')
def query_sellers_admins():
    sellers = db.session.query(User.email).filter(User.role=='owner')
    admins = db.session.query(User.email).filter(User.role=='admin')
    emails = sellers.union(admins).all()
    return render_template('results.html', title="Sellers and Admin Emails", results=emails)


@app.route('/query_role_specific')
def query_role_specific():
    # Only one query, using positional WHEN tuples
    results = db.session.query(
        User.name,
        case(
            (User.role == 'renter', 'Customer'),
            (User.role == 'owner', 'Product Lister'),
            (User.role == 'admin', 'Administrator'),
            else_='Unknown'
        ).label('role_label')
    ).all()

    return render_template('results.html',
                           title="Role Specific Names",
                           results=results)



@app.route('/query_filter_mens_tuxedo')
def query_filter_mens_tuxedo():
    results = Product.query.filter(
        Product.category=='mens',
        Product.sub_category=='tuxedo',
        Product.rental_price < 1500
    ).all()
    return render_template('results.html', title="Mens Tuxedo Under 1500", results=results)


@app.route('/query_filter_womens_rating')
def query_filter_womens_rating():
    results = db.session.query(
                Product.product_id,
                Product.name,
                Product.rental_price,
                func.avg(Review.rating).label('avg_rating')
              ).join(Review, Review.product_id == Product.product_id
              ).filter(
                  Product.category=='womens',
                  Product.rental_price < 1300
              ).group_by(Product.product_id, Product.name, Product.rental_price
              ).having(func.avg(Review.rating) >= 4).all()
    return render_template('results.html', title="Womens Products with Avg Rating >= 4", results=results)


@app.route('/query_filter_accessories_cleaned')
def query_filter_accessories_cleaned():
    today = date.today()
    first_day_last_month = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
    last_month = first_day_last_month.month
    year_month = first_day_last_month.year
    results = db.session.query(
                Product.product_id,
                Product.name,
                Product.available_quantity,
                Maintenance.last_cleaned
              ).join(Maintenance, Maintenance.product_id == Product.product_id
              ).filter(
                  Product.category == 'accessories',
                  Product.available_quantity > 3,
                  func.MONTH(Maintenance.last_cleaned)== last_month,
                  func.YEAR(Maintenance.last_cleaned)== year_month
              ).all()
    return render_template('results.html', title="Accessories Cleaned Last Month", results=results)


@app.route('/query_sort_products_avg_rating')
def query_sort_products_avg_rating():
    results = db.session.query(
                Product.product_id,
                Product.name,
                Product.category,
                func.avg(Review.rating).label("avg_rating")
              ).join(Review, Review.product_id == Product.product_id
              ).filter(Product.category.in_(['mens','womens'])
              ).group_by(Product.product_id, Product.name, Product.category
              ).order_by(func.avg(Review.rating).desc()
              ).all()
    return render_template('results.html', title="Mens & Womens Products Sorted by Avg Rating", results=results)


@app.route('/query_multifunction_users')
def query_multifunction_users():
    subq_products = db.session.query(
                    Product.owner_id.label('user_id'),
                    func.count(Product.product_id).label('total_products_listed')
                 ).group_by(Product.owner_id).subquery()
    subq_rentals = db.session.query(
                    Rental.renter_id.label('user_id'),
                    func.sum(Rental.total_cost).label('total_spent_on_rentals')
                 ).group_by(Rental.renter_id).subquery()
    results = db.session.query(
                    User.user_id, User.name, User.email,
                    subq_products.c.total_products_listed,
                    subq_rentals.c.total_spent_on_rentals
              ).join(subq_products, User.user_id == subq_products.c.user_id
              ).join(subq_rentals, User.user_id == subq_rentals.c.user_id
              ).filter(
                  subq_products.c.total_products_listed > 2,
                  subq_rentals.c.total_spent_on_rentals > 700
              ).all()
    return render_template('results.html', title="Multi-functional Users", results=results)


@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        name     = request.form['name']
        email    = request.form['email']
        phone    = request.form['phone']
        password = request.form['password']
        role     = request.form['role']
        # Simple uniqueness check
        if User.query.filter_by(email=email).first():
            flash("Email already registered", "error")
            return redirect(url_for('register'))

        new_user = User(name=name, email=email, phone=phone, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.", "success")
        return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email    = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email, password=password).first()
        if user:
            session['user_id'] = user.user_id
            flash(f"Welcome back, {user.name}!", "success")
            return redirect(url_for('index'))
        else:
            flash("Incorrect credentials", "error")
            return redirect(url_for('login'))

    return render_template('login.html')


@app.route('/rent_item', methods=['GET','POST'])
def rent_item():
    # must be logged in
    if 'user_id' not in session:
        flash("Please log in to add a product", "error")
        return redirect(url_for('login'))

    if request.method == 'POST':
        name     = request.form['name']
        category = request.form['category']
        sub_cat  = request.form['sub_category']
        price    = request.form['rental_price']
        qty      = request.form['available_quantity']

        product = Product(
            name=name,
            category=category,
            sub_category=sub_cat,
            owner_id=session['user_id'],
            rental_price=price,
            available_quantity=qty
        )
        db.session.add(product)
        db.session.commit()
        flash("Product added successfully!", "success")
        return redirect(url_for('index'))

    return render_template('rent_item.html')


@app.route('/sort_products_price')
def sort_products_price():
    products = Product.query.order_by(Product.rental_price).all()
    return render_template('results.html',
                           title="Products Sorted by Price",
                           results=products)

#########################################
# MAIN
#########################################

if __name__ == '__main__':
    app.run(debug=True)
