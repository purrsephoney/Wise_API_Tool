

import requests
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Globals
active_profile_id = None
display_name = None
profile_type = None

# Config
BASE_URL = os.getenv("WISE_BASE_URL", "https://api.wise-sandbox.com")
TOKEN = os.getenv("WISE_TOKEN")

# Static Endpoints
CURRENCIES = "/v1/currencies"
PROFILES = "/v1/profiles"
QUOTES_ANONYMOUS = "/v3/quotes"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# Boot functions 
def fetch_currencies():
    response = requests.get(f"{BASE_URL}{CURRENCIES}", headers=HEADERS)
    if response.status_code != 200:
        handle_api_error(response, context="Fetch currencies")
        exit()
    return response.json()

def fetch_profiles():
    response = requests.get(f"{BASE_URL}{PROFILES}", headers=HEADERS)
    if response.status_code != 200:
        handle_api_error(response, context="Fetch profiles")
        exit()
    return response.json()

def create_quote(inputs, active_profile_id, user_intent):
    body = build_quote_body(
        inputs,
        active_profile_id if user_intent == "make_transfer" else None
    )

    if active_profile_id and user_intent == "make_transfer":
        url = f"{BASE_URL}/v3/profiles/{active_profile_id}/quotes" #build the URL inline bc it needs variable expansion
    else:
        url = f"{BASE_URL}{QUOTES_ANONYMOUS}"

    response = requests.post(url, headers=HEADERS, json=body)

    if response.status_code != 200:
        handle_api_error(response, context="Create quote")
        return None

    return response.json()

def select_profile(profiles):
    print("\nSelect a profile:")
    for i, profile in enumerate(profiles):
        if profile["type"] == "business":
            display_name = profile["details"]["name"]
        else:
            display_name = f"{profile['details']['firstName']} {profile['details']['lastName']}"
        print(f"{i + 1}. {display_name} ({profile['type'].capitalize()})")

    while True:
        try:
            choice = int(input("\nEnter number: ")) - 1
            if 0 <= choice < len(profiles):
                selected = profiles[choice]
                if selected["type"] == "business":
                    display_name = selected["details"]["name"]
                else:
                    display_name = f"{selected['details']['firstName']} {selected['details']['lastName']}"
                return selected["id"], display_name, selected["type"]
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Please enter a number.")

# Currency helper
def find_currency(user_input, currencies, max_suggestions=3):
    user_input_lower = user_input.lower()
    
    for currency in currencies:
        if user_input_lower == currency["code"].lower():
            return currency["code"], []
    
    # skip currencies with catch-all keyword lists (e.g. EUR, GBP, USD)
    for currency in currencies:
        if len(currency.get("countryKeywords", [])) > 20:
            continue
        keywords = [k.lower() for k in currency.get("countryKeywords", [])]
        if user_input_lower in keywords:
            return currency["code"], []
    
    suggestions = []
    for currency in currencies:
        if (user_input_lower in currency["code"].lower() or
            user_input_lower in currency["name"].lower()):
            suggestions.append(f"{currency['code']} ({currency['name']})")
    
    return None, suggestions[:max_suggestions]

# Quote inputs 
def get_quote_inputs(currencies):
    while True:
        source_input = input("\nSource currency (name or code, or 'r' to restart): ")
        if source_input.lower() == "r":
            return None
        source_currency, suggestions = find_currency(source_input, currencies)
        if source_currency:
            break
        if suggestions:
            print(f"'{source_input}' not found. Did you mean:")
            for s in suggestions:
                print(f"   - {s}")
        else:
            print(f"'{source_input}' not found. Try a 3-letter code (e.g. GBP) or country name.")

    while True:
        target_input = input("Target currency (name or code, or 'r' to restart): ")
        if target_input.lower() == "r":
            return None
        target_currency, suggestions = find_currency(target_input, currencies)
        if target_currency:
            break
        if suggestions:
            print(f"'{target_input}' not found. Did you mean:")
            for s in suggestions:
                print(f"   - {s}")
        else:
            print(f"'{target_input}' not found. Try a 3-letter code (e.g. GBP) or country name.")

    print(f"\nTransfer {source_currency} → {target_currency}")
    print("1. Send")
    print("2. Receive")

    while True:
        amount_choice = input("\nEnter choice (1 or 2): ").strip()
        if amount_choice in ["1", "2"]:
            break
        print("Please enter 1 or 2.")

    while True:
        try:
            if amount_choice == "1":
                amount = float(input(f"How much {source_currency} to send? "))
            else:
                amount = float(input(f"How much {target_currency} to receive? "))
            if amount > 0:
                break
            print("Amount must be greater than 0.")
        except ValueError:
            print("Please enter a valid number.")

    source_amount = amount if amount_choice == "1" else None
    target_amount = amount if amount_choice == "2" else None

    return {
        "sourceCurrency": source_currency,
        "targetCurrency": target_currency,
        "sourceAmount": source_amount,
        "targetAmount": target_amount
    }

# Quote builder 
def build_quote_body(inputs, active_profile_id=None):
    body = {
        "sourceCurrency": inputs["sourceCurrency"],
        "targetCurrency": inputs["targetCurrency"],
        "sourceAmount": inputs["sourceAmount"],
        "targetAmount": inputs["targetAmount"]
    }
    if active_profile_id:
        body["profile"] = active_profile_id
        body["targetAccount"] = None
        body["preferredPayIn"] = "BALANCE"
    return body


def display_quote(quote):
    enabled_options = [o for o in quote["paymentOptions"] if not o["disabled"]]
    if not enabled_options:
        reasons = set()
        for option in quote["paymentOptions"]:
            if option.get("disabledReason") and option["disabledReason"].get("message"):
                reasons.add(option["disabledReason"]["message"])
        
        if reasons:
            for reason in reasons:
                print(f"\n⚠️  {reason}")
        elif quote.get("notices"):
            for notice in quote["notices"]:
                print(f"\n⚠️  {notice['text']}")
        return None

    first = enabled_options[0]
    top_3 = enabled_options[:3]

    source_amount = first["sourceAmount"]
    source_currency = first["sourceCurrency"]
    target_amount = first["targetAmount"]
    target_currency = first["targetCurrency"]
    expiry = datetime.strptime(quote['expirationTime'], "%Y-%m-%dT%H:%M:%SZ")

    print("\n" + "=" * 50)
    print(f"Profile:   {display_name} ({profile_type.capitalize()})")
    print(f"Quote ID:  {quote['id']}")
    print(f"Rate:      1 {source_currency} = {quote['rate']} {target_currency}")
    print(f"You send:  {source_amount} {source_currency}")
    print(f"They get:  {target_amount} {target_currency}")
    print(f"Expires:   {expiry.strftime('%d %b %Y %H:%M')} UTC")

    print("\nPayment options:")
    print(f"{'#':<4} {'Method':<25} {'Fee':<10} {'You send':<12} {'They receive':<15} {'Delivery'}")
    print("-" * 85)

    for i, option in enumerate(top_3, 1):
        print(
            f"{i:<4} "
            f"{option['payIn']:<25} "
            f"{option['fee']['total']:<10} "
            f"{option['sourceAmount']:<6} {option['sourceCurrency']:<6} "
            f"{option['targetAmount']:<6} {option['targetCurrency']:<6} "
            f"{option['formattedEstimatedDelivery']}"
        )
    print("=" * 85)
    if quote.get("notices"):
        for notice in quote["notices"]:
            print(f"\n⚠️  {notice['text']}")

def handle_api_error(response, context="Request"):
    status = response.status_code
    try:
        body = response.json()
        message = body.get("errors", [{}])[0].get("message", "No details provided")
    except:
        message = response.text

    errors = {
        401: "Authentication failed — check your API token.",
        403: "Access denied — token may have insufficient permissions.",
        404: "Resource not found — check your profile ID.",
        422: f"Request rejected: {message}",
        429: "Rate limit exceeded — please wait before retrying.",
        500: "Wise server error — try again later or check status.wise.com"
    }
    print(f"\n {context} failed ({status}): {errors.get(status, message)}")


def main():
    print("Initialising Wise Quote Tool...")

    if not TOKEN:
        print("Error: WISE_TOKEN not found. Check your .env file.")
        exit()

    currencies = fetch_currencies()
    profiles = fetch_profiles()
    global active_profile_id, display_name, profile_type
    active_profile_id, display_name, profile_type = select_profile(profiles)

    print(f"\nWelcome, {display_name}!")

    while True:
        print("\nWhat would you like to do?")
        print("1. Check rates")
        print("2. Get a quote for transfer")
        print("3. Switch profile")
        print("4. Exit")

        choice = input("\nEnter choice: ").strip()

        if choice == "4":
            print("Goodbye!")
            break
        elif choice not in ["1", "2", "3"]:
            print("Please enter 1, 2, 3 or 4.")
            continue

        if choice == "3":
            active_profile_id, display_name, profile_type = select_profile(profiles)
            print(f"\nSwitched to {display_name}!")
            continue

        user_intent = "check_rates" if choice == "1" else "make_transfer"

        inputs = get_quote_inputs(currencies)
        if inputs is None:
            continue

        print(f"\nYou want to {'send' if inputs['sourceAmount'] else 'receive'} "
              f"{inputs['sourceAmount'] or inputs['targetAmount']} "
              f"{'from' if inputs['sourceAmount'] else 'in'} "
              f"{inputs['sourceCurrency']} → {inputs['targetCurrency']}")

        confirm = input("Confirm? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled.")
            continue

        quote = create_quote(inputs, active_profile_id, user_intent)
        if quote:
            display_quote(quote)


if __name__ == "__main__":
    main()