# Wise Quote Tool

A Python CLI integration demonstrating the Wise Platform API quote flow.

## What it does
- Authenticates using a Wise personal API token
- Fetches profiles associated with the account
- Validates currency input against Wise's supported currencies
- Creates authenticated and anonymous quotes
- Displays payment options, fees, and delivery estimates

## Prerequisites
- Python 3
- A Wise account with a personal API token (Full Access)

## Setup
1. Install dependencies:
   pip install requests python-dotenv

2. Create a `.env` file in the project root:
   WISE_TOKEN=your_token_here
   WISE_BASE_URL=https://api.wise-sandbox.com

## Run
   python3 app.py