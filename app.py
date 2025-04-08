from flask import Flask, request, jsonify
import requests
import os
import re
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
AUTH_NET_API_LOGIN_ID = os.getenv("AUTH_NET_API_LOGIN_ID")
AUTH_NET_TRANSACTION_KEY = os.getenv("AUTH_NET_TRANSACTION_KEY")
AUTH_NET_ENDPOINT = os.getenv("AUTH_NET_ENDPOINT") or "https://apitest.authorize.net/xml/v1/request.api"

SHOPIFY_API_KEY = os.getenv("SHOPIFY_API_KEY")
SHOPIFY_API_PASSWORD = os.getenv("SHOPIFY_API_PASSWORD")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")

def extract_numeric_id(order_id):
    if isinstance(order_id, str) and order_id.startswith("gid://"):
        return re.findall(r"\d+", order_id)[-1]
    return str(order_id)

def build_auth_capture_xml(amount, po_number, tax_amount, shipping_zip, line_items, shipping_address):
    item_block = ""
    for item in line_items:
        item_block += f"""
        <lineItem>
            <itemId>{item['sku']}</itemId>
            <name>{item['name']}</name>
            <quantity>{item['quantity']}</quantity>
            <unitPrice>{item['unit_price']}</unitPrice>
            <taxAmount>{item['tax_amount']}</taxAmount>
        </lineItem>"""

    ship_to_block = ""
    if shipping_address:
        ship_to_block = f"""
    <shipTo>
      <firstName>{shipping_address.get("first_name", "")}</firstName>
      <lastName>{shipping_address.get("last_name", "")}</lastName>
      <address>{shipping_address.get("address1", "")}</address>
      <city>{shipping_address.get("city", "")}</city>
      <state>{shipping_address.get("province", "")}</state>
      <zip>{shipping_address.get("zip", "")}</zip>
      <country>{shipping_address.get("country", "")}</country>
    </shipTo>"""

    return f"""<?xml version="1.0" encoding="utf-8"?>
<createTransactionRequest xmlns="AnetApi/xml/v1/schema/AnetApiSchema.xsd">
  <merchantAuthentication>
    <name>{AUTH_NET_API_LOGIN_ID}</name>
    <transactionKey>{AUTH_NET_TRANSACTION_KEY}</transactionKey>
  </merchantAuthentication>
  <transactionRequest>
    <transactionType>authCaptureTransaction</transactionType>
    <amount>{amount}</amount>
    <payment>
      <creditCard>
        <cardNumber>4111111111111111</cardNumber>
        <expirationDate>2026-12</expirationDate>
        <cardCode>123</cardCode>
      </creditCard>
    </payment>
    <order>
      <invoiceNumber>{po_number}</invoiceNumber>
      <description>Shopify Order</description>
    </order>
    <lineItems>{item_block}
    </lineItems>
    <tax>
      <amount>{tax_amount}</amount>
      <name>Sales Tax</name>
      <description>Local sales tax</description>
    </tax>
    <customer>
      <id>shopify</id>
    </customer>
    <billTo>
      <zip>{shipping_zip}</zip>
    </billTo>{ship_to_block}
  </transactionRequest>
</createTransactionRequest>
"""

@app.route("/webhook", methods=["POST"])
def webhook():
    logger.info("Webhook received")

    data = request.get_json()
    logger.info("Incoming payload: %s", data)

    raw_order_id = data.get("order_id")
    po_number = data.get("po_number", "").strip() or "N/A"

    if not raw_order_id:
        logger.error("Missing order_id")
        return "Missing order_id", 400

    order_id = extract_numeric_id(raw_order_id)
    url = f"https://{SHOPIFY_API_KEY}:{SHOPIFY_API_PASSWORD}@{SHOPIFY_STORE}/admin/api/2023-10/orders/{order_id}.json"
    response = requests.get(url)

    if response.status_code != 200:
        logger.error("Failed to fetch order: %s", response.text)
        return f"Failed to fetch order: {response.text}", 500

    order = response.json()["order"]
    logger.info("Order pulled successfully: %s", order.get("name"))

    shipping_address = order.get("shipping_address", {})
    shipping_zip = shipping_address.get("zip", "00000")
    total_tax = order.get("total_tax", 0)

    line_items = []
    for item in order.get("line_items", []):
        tax_amount = 0
        if item.get("tax_lines"):
            tax_amount = float(item["tax_lines"][0]["price"])
        line_items.append({
            "sku": item.get("sku"),
            "name": item.get("title"),
            "quantity": item.get("quantity"),
            "unit_price": item.get("price"),
            "tax_amount": tax_amount
        })

    total_amount = sum(float(i["unit_price"]) * i["quantity"] for i in line_items)

    xml = build_auth_capture_xml(
        amount=total_amount,
        po_number=po_number,
        tax_amount=total_tax,
        shipping_zip=shipping_zip,
        line_items=line_items,
        shipping_address=shipping_address
    )

    logger.info("Sending XML to Authorize.net:\n%s", xml)

    authnet_response = requests.post(
        AUTH_NET_ENDPOINT,
        data=xml.encode("utf-8"),
        headers={"Content-Type": "application/xml"}
    )

    logger.info("Authorize.net response [%s]: %s", authnet_response.status_code, authnet_response.text)

    return jsonify({"status": "sent to Authorize.net"}), 200
