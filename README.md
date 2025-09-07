# Money Maker

A simple Flask app to help you ideate monetizable projects, estimate pricing, and publish quick landing pages with email capture and optional Stripe checkout.

## Features

- Idea Generator: prompt-based ideas with monetization angles
- Pricing Calculator: derive price tiers from MRR and traffic assumptions
- Landing Page Builder: publish a page with email capture and optional Stripe link
- SQLite persistence for pages and signups

## Requirements

- Python 3.9+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000

## Environment

- `SECRET_KEY` (optional): Flask secret for sessions
- `DATABASE_URL` (optional): default is `sqlite:///app.db`

## Notes

- Email capture is stored locally in SQLite. For production, add an ESP integration (e.g., ConvertKit, Mailchimp) or export via admin page.
- To use Stripe, create a Checkout link in your dashboard and paste the URL when creating a page.
