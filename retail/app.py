from flask import Flask, render_template, request, redirect, url_for, session, \
    flash, jsonify
import json
import os
from pathlib import Path

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # For session management


# Data setup - in a real app you'd use a database
def get_data_folder():
    """Get the data folder path."""
    return Path(__file__).parent.parent / 'data'


def load_products():
    """Load products from the data file."""
    try:
        with open(get_data_folder() / 'products.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Create products.json if it doesn't exist
        products = [
            {
                "name": "laptop",
                "price": 999.99,
                "description": "High-quality laptop with powerful specs",
                "stock": 10
            },
            {
                "name": "phone",
                "price": 499.99,
                "description": "Latest smartphone with great features",
                "stock": 15
            },
            {
                "name": "headphones",
                "price": 99.99,
                "description": "Noise-cancelling wireless headphones",
                "stock": 20
            },
            {
                "name": "keyboard",
                "price": 59.99,
                "description": "Mechanical gaming keyboard",
                "stock": 8
            }
        ]

        os.makedirs(get_data_folder(), exist_ok=True)
        with open(get_data_folder() / 'products.json', 'w') as f:
            json.dump(products, f)

        return products


def save_products(products):
    """Save products to the data file."""
    os.makedirs(get_data_folder(), exist_ok=True)
    with open(get_data_folder() / 'products.json', 'w') as f:
        json.dump(products, f)


def find_product(name):
    """Find a product by name."""
    products = load_products()
    for product in products:
        if product['name'].lower() == name.lower():
            return product
    return None


def is_product_in_stock(name, quantity=1):
    """Check if a product is in stock."""
    product = find_product(name)
    if not product:
        return False, "Product not found"
    if product['stock'] <= 0:
        return False, "This product is currently out of stock"
    if product['stock'] < quantity:
        return False, f"Only {product['stock']} units available"
    return True, product


# Routes
@app.route('/')
def index():
    """Home page that displays all products."""
    products = load_products()
    cart = session.get('cart', [])
    cart_count = sum(item.get('quantity', 0) for item in cart)
    error = session.pop('error', None)
    success = session.pop('success', None)

    return render_template('index.html',
                           products=products,
                           cart=cart,
                           cart_count=cart_count,
                           error=error,
                           success=success)


@app.route('/search', methods=['POST'])
def search():
    """Search for products."""
    product_name = request.form.get('product_name', '')

    if not product_name:
        session['error'] = "Please enter a product name"
        return redirect(url_for('index'))

    product = find_product(product_name)

    if not product:
        session['error'] = "Product not found"
        return redirect(url_for('index'))

    return render_template('product.html',
                           product=product,
                           cart=session.get('cart', []))


@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    """Add products to cart."""
    product_name = request.form.get('product_name', '')
    quantity = request.form.get('quantity', '1')

    try:
        quantity = int(quantity)
        if quantity <= 0:
            flash("Quantity must be greater than 0")
            return redirect(url_for('index'))
    except ValueError:
        flash("Invalid quantity")
        return redirect(url_for('index'))

    in_stock, product_or_message = is_product_in_stock(product_name, quantity)

    if not in_stock:
        flash(product_or_message)
        return redirect(url_for('index'))

    # Product exists and is in stock
    product = product_or_message
    cart = session.get('cart', [])

    # Check if product already in cart
    found = False
    for item in cart:
        if item['name'].lower() == product_name.lower():
            item['quantity'] += quantity
            found = True
            break

    if not found:
        cart.append({
            'name': product['name'],
            'price': product['price'],
            'quantity': quantity
        })

    session['cart'] = cart
    flash(f"Added {quantity} {product_name}(s) to cart")
    return redirect(url_for('index'))


@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    """Checkout process."""
    cart = session.get('cart', [])

    # Check for empty cart
    if not cart:
        flash("Cart is empty")
        return redirect(url_for('index'))

    # Check for simulated checkout error
    if session.get('simulate_checkout_error'):
        session.pop('simulate_checkout_error', None)
        flash("An unexpected error occurred during checkout")
        return redirect(url_for('index'))

    # Check stock for all items
    products = load_products()
    for item in cart:
        for product in products:
            if product['name'].lower() == item['name'].lower():
                if product['stock'] < item['quantity']:
                    flash(
                        f"{item['name']} is out of stock. Only {product['stock']} available.")
                    return redirect(url_for('index'))
                break

    # Process order - update stock
    for item in cart:
        for product in products:
            if product['name'].lower() == item['name'].lower():
                product['stock'] -= item['quantity']
                break

    save_products(products)

    # Clear cart
    session['cart'] = []
    flash("Thank you for your purchase!")
    return redirect(url_for('index'))


@app.route('/cart')
def view_cart():
    """View shopping cart."""
    cart = session.get('cart', [])
    total = sum(
        item.get('price', 0) * item.get('quantity', 0) for item in cart)
    return render_template('cart.html', cart=cart, total=total)


@app.route('/clear_cart')
def clear_cart():
    """Clear the shopping cart."""
    session['cart'] = []
    flash("Cart has been cleared")
    return redirect(url_for('index'))


@app.route('/simulate_out_of_stock')
def simulate_out_of_stock():
    """Simulate a product going out of stock."""
    products = load_products()

    # Find the product in the cart and set its stock to 0
    cart = session.get('cart', [])
    if cart:
        for product in products:
            if product['name'].lower() == cart[0]['name'].lower():
                product['stock'] = 0
                save_products(products)
                break

    flash("Stock levels have been updated")
    return redirect(url_for('index'))


@app.route('/simulate_checkout_error')
def simulate_checkout_error():
    """Simulate an error during checkout."""
    session['simulate_checkout_error'] = True
    return redirect(url_for('index'))


# Error handling
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('error.html', error="Page not found"), 404


@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('error.html',
                           error="An unexpected error occurred"), 500


if __name__ == '__main__':
    # Create data directory if it doesn't exist
    os.makedirs(get_data_folder(), exist_ok=True)

    # Ensure product data exists
    load_products()

    app.run(debug=True, host='0.0.0.0', port=8080)