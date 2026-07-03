"""
External Services Layer
-------------------------
Stands in for "SBI APIs / Partners" — mutual funds, billers, payments, KYC,
credit bureau. All mocked so the prototype is self-contained; each function
is where a real SBI/YONO API call or partner integration would go.
"""
import random
import time


def invest_in_liquid_fund(user_id, amount):
    time.sleep(0.2)  # simulate network latency
    return {
        "status": "success",
        "reference_id": f"MF{random.randint(100000, 999999)}",
        "fund": "SBI Liquid Fund - Direct Growth",
        "amount": amount,
        "expected_annual_return": "6.1% - 6.5%",
    }


def pay_bill(user_id, biller, amount):
    time.sleep(0.15)
    return {
        "status": "success",
        "reference_id": f"BILL{random.randint(100000, 999999)}",
        "biller": biller,
        "amount": amount,
    }


def start_sip(user_id, label, amount):
    time.sleep(0.15)
    return {
        "status": "success",
        "reference_id": f"SIP{random.randint(100000, 999999)}",
        "label": label,
        "amount": amount,
        "next_debit": "1st of next month",
    }


def send_push_notification(user_id, title, message):
    # Would call FCM in production.
    return {"channel": "push", "delivered": True, "title": title, "message": message}


def send_email_sms(user_id, title, message):
    return {"channel": "email_sms", "delivered": True, "title": title, "message": message}
