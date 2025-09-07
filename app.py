import os
from datetime import datetime
from typing import List, Dict

from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from slugify import slugify


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)


class LandingPage(db.Model):
	__tablename__ = "landing_pages"

	id = db.Column(db.Integer, primary_key=True)
	title = db.Column(db.String(200), nullable=False)
	slug = db.Column(db.String(200), unique=True, nullable=False)
	hero_text = db.Column(db.Text, nullable=False)
	value_prop = db.Column(db.Text, nullable=False)
	cta_text = db.Column(db.String(120), nullable=False)
	price = db.Column(db.String(50), nullable=True)
	stripe_url = db.Column(db.String(300), nullable=True)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

	email_signups = db.relationship("EmailSignup", backref="landing_page", lazy=True, cascade="all, delete-orphan")

	def __repr__(self) -> str:
		return f"<LandingPage slug={self.slug!r}>"


class EmailSignup(db.Model):
	__tablename__ = "email_signups"

	id = db.Column(db.Integer, primary_key=True)
	landing_page_id = db.Column(db.Integer, db.ForeignKey("landing_pages.id"), nullable=False)
	email = db.Column(db.String(200), nullable=False)
	created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

	def __repr__(self) -> str:
		return f"<EmailSignup email={self.email!r} page_id={self.landing_page_id}>"


with app.app_context():
	db.create_all()


@app.route("/")
def index():
	return render_template("home.html")


@app.route("/ideas", methods=["GET", "POST"])
def ideas():
	generated_ideas: List[Dict[str, str]] = []
	if request.method == "POST":
		industry = request.form.get("industry", "").strip()
		audience = request.form.get("audience", "").strip()
		skills = request.form.get("skills", "").strip()

		keywords = [
			industry or "niche",
			audience or "buyers",
			skills or "skills",
		]

		patterns = [
			("Paid newsletter", "Weekly deep-dives, benchmarks, and templates; upsell cohort courses"),
			("Niche job board", "Charge companies per post; add subscriptions for candidates"),
			("Directory/marketplace", "Listing fees + featured placements; take a % fee on transactions"),
			("Micro-SaaS tool", "Subscription with 2-3 tiers; add onboarding service for $$$"),
			("Template pack", "One-time purchase + extended license upsell; affiliate bundles"),
			("Cohort course", "High-ticket with alumni community; offer corporate packages"),
			("Automation service", "Done-for-you monthly retainer; productize common workflows"),
		]

		for base_name, monetization in patterns:
			name = f"{keywords[0].title()} {base_name} for {keywords[1].title()}"
			description = f"Leverage {keywords[2]} to deliver outcomes for {audience or 'your niche'}"
			generated_ideas.append({
				"name": name,
				"description": description,
				"monetization": monetization,
			})

	return render_template("ideas.html", ideas=generated_ideas)


@app.route("/pricing", methods=["GET", "POST"])
def pricing():
	result = None
	if request.method == "POST":
		try:
			target_mrr = float(request.form.get("target_mrr", 0) or 0)
			conversion_rate = float(request.form.get("conversion_rate", 0) or 0) / 100.0
			monthly_visitors = float(request.form.get("monthly_visitors", 0) or 0)
			cost_per_unit = float(request.form.get("cost_per_unit", 0) or 0)

			buyers_per_month = max(0.0, monthly_visitors * conversion_rate)
			base_price = (target_mrr / buyers_per_month) if buyers_per_month > 0 else 0.0
			required_price = max(0.0, base_price + cost_per_unit)

			price_low = round(required_price * 0.8, 2)
			price_mid = round(required_price, 2)
			price_high = round(required_price * 1.5, 2)

			result = {
				"buyers_per_month": int(buyers_per_month),
				"price_low": price_low,
				"price_mid": price_mid,
				"price_high": price_high,
			}
		except ValueError:
			flash("Invalid input. Please enter numeric values.", "error")

	return render_template("pricing.html", result=result)


@app.route("/pages")
def pages_list():
	pages = LandingPage.query.order_by(LandingPage.created_at.desc()).all()
	counts = {
		page.id: EmailSignup.query.filter_by(landing_page_id=page.id).count() for page in pages
	}
	return render_template("pages_list.html", pages=pages, counts=counts)


@app.route("/pages/new", methods=["GET", "POST"])
def new_page():
	if request.method == "POST":
		title = request.form.get("title", "").strip()
		hero_text = request.form.get("hero_text", "").strip()
		value_prop = request.form.get("value_prop", "").strip()
		cta_text = request.form.get("cta_text", "").strip()
		price = request.form.get("price", "").strip()
		stripe_url = request.form.get("stripe_url", "").strip()

		if not title or not hero_text or not value_prop or not cta_text:
			flash("Please fill in all required fields.", "error")
			return render_template("new_page.html")

		slug_base = slugify(title) or slugify(hero_text[:30]) or "page"
		slug = slug_base
		counter = 2
		while LandingPage.query.filter_by(slug=slug).first() is not None:
			slug = f"{slug_base}-{counter}"
			counter += 1

		page = LandingPage(
			title=title,
			slug=slug,
			hero_text=hero_text,
			value_prop=value_prop,
			cta_text=cta_text,
			price=price,
			stripe_url=stripe_url or None,
		)
		db.session.add(page)
		db.session.commit()
		flash("Landing page created!", "success")
		return redirect(url_for("view_page", slug=page.slug))

	return render_template("new_page.html")


@app.route("/p/<slug>")
def view_page(slug: str):
	page = LandingPage.query.filter_by(slug=slug).first_or_404()
	return render_template("view_page.html", page=page)


@app.route("/p/<slug>/signup", methods=["POST"])
def signup_email(slug: str):
	page = LandingPage.query.filter_by(slug=slug).first_or_404()
	email = request.form.get("email", "").strip()
	if not email:
		flash("Please provide an email.", "error")
		return redirect(url_for("view_page", slug=slug))

	signup = EmailSignup(landing_page_id=page.id, email=email)
	db.session.add(signup)
	db.session.commit()
	flash("Thanks! We will be in touch.", "success")
	return redirect(url_for("view_page", slug=slug))


if __name__ == "__main__":
	port = int(os.environ.get("PORT", 5000))
	app.run(host="0.0.0.0", port=port, debug=True)