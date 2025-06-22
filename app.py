from datetime import datetime
from flask import (
    Flask, render_template, request, redirect, url_for, flash
)
from flask_sqlalchemy import SQLAlchemy
import json
import os
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///fest.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'REPLACE_ME'  # für Flash‑Messages
db = SQLAlchemy(app)

# ---------------------
# Datenbank‑Modelle
# ---------------------
class Drink(db.Model):
    id       = db.Column(db.Integer, primary_key=True)
    name     = db.Column(db.String(40), nullable=False)
    size_ml  = db.Column(db.Integer, nullable=False)
    price    = db.Column(db.Numeric(5, 2), nullable=False)

class Order(db.Model):
    id               = db.Column(db.Integer, primary_key=True)
    waiter_name      = db.Column(db.String(30), nullable=False)
    created_at       = db.Column(db.DateTime, default=datetime.utcnow)
    schankwagen_done = db.Column(db.Boolean, default=False)
    bedienung_done   = db.Column(db.Boolean, default=False)
    items            = db.relationship('OrderItem', backref='order',
                                        cascade='all, delete-orphan')

class OrderItem(db.Model):
    id        = db.Column(db.Integer, primary_key=True)
    order_id  = db.Column(db.Integer, db.ForeignKey('order.id'),
                          nullable=False)
    drink_id  = db.Column(db.Integer, db.ForeignKey('drink.id'),
                          nullable=False)
    qty       = db.Column(db.Integer, nullable=False)
    drink     = db.relationship('Drink')

# ---------------------
# Hilfsfunktionen
# ---------------------
def seed_drinks():
    # Pfad zur JSON
    cfg_path = os.path.join(os.path.dirname(__file__),
                            'config', 'drinks.json')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        drinks = json.load(f)

    # 1) Alle bisherigen Drinks löschen
    Drink.query.delete()
    db.session.commit()

    # 2) Nur noch Drinks aus der JSON einfügen
    for d in drinks:
        db.session.add(Drink(
            name    = d['name'],
            size_ml = d['size_ml'],
            price   = d['price']
        ))
    db.session.commit()

# ---------------------
# Routen – Bedienung
# ---------------------
@app.route('/', methods=['GET', 'POST'])
def order():
    drinks = Drink.query.all()
    if request.method == 'POST':
        waiter = request.form['waiter_name'].strip()
        if not waiter:
            flash("Name der Bedienung angeben!", "warning")
            return redirect(url_for('order'))
        quantities = {
            int(k.split('_')[1]): int(v)
            for k, v in request.form.items() if k.startswith('qty_') and v
        }
        if not quantities:
            flash("Bitte mindestens ein Getränk wählen.", "warning")
            return redirect(url_for('order'))

        new_order = Order(waiter_name=waiter)
        for drink_id, qty in quantities.items():
            new_order.items.append(OrderItem(drink_id=drink_id, qty=qty))
        db.session.add(new_order)
        db.session.commit()
        flash(f"Bestellung #{new_order.id} erfasst!", "success")
        return redirect(url_for('waiter_orders', waiter_name=waiter))
    return render_template('order.html', drinks=drinks)

@app.route('/orders/<waiter_name>')
def waiter_orders(waiter_name):
    orders = (Order.query
              .filter_by(waiter_name=waiter_name)
              .order_by(Order.created_at.desc())
              .all())
    # Berechne pro Bestellung die Summe:
    for o in orders:
        o.total = sum(item.qty * float(item.drink.price) for item in o.items)
    return render_template('waiter_orders.html',
                           orders=orders, waiter=waiter_name)

@app.post('/orders/<int:order_id>/close')
def waiter_close(order_id):
    order = Order.query.get_or_404(order_id)
    order.bedienung_done = True
    db.session.commit()
    flash(f"Bestellung #{order.id} abgeschlossen.", "info")
    return redirect(url_for('waiter_orders', waiter_name=order.waiter_name))

# ---------------------
# Routen – Schankwagen
# ---------------------
@app.route('/monitor')
def monitor():
    open_orders = (Order.query
                   .filter_by(schankwagen_done=False)
                   .order_by(Order.created_at.asc())
                   .all())
    return render_template('monitor.html', orders=open_orders)

@app.post('/monitor/<int:order_id>/done')
def schankwagen_done(order_id):
    order = Order.query.get_or_404(order_id)
    order.schankwagen_done = True
    db.session.commit()
    flash(f"Bestellung #{order.id} fertig!", "success")
    return redirect(url_for('monitor'))

# ---------------------
# App‑Start
# ---------------------
if __name__ == '__main__':
   # DB-Initialisierung im App-Kontext
    with app.app_context():
        db.create_all()
        seed_drinks()

    # Server starten
    app.run(host='0.0.0.0', port=5000, debug=True)