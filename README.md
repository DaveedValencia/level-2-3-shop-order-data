# Shopify to Authorize.net Level 2 & 3 Integration

## 🧾 Project Summary

**Goal:**  
Send Level 2 and 3 credit card data from Shopify orders to Authorize.net for VA compliance, including line items, PO number, tax, and shipping ZIP.

**Status:**  
Hybrid testing: Shopify (live store in test mode) → Authorize.net (sandbox environment)

---

## 🛒 Shopify Configuration

- **Store Type:** Production store (test mode enabled)
- **Checkout Settings:** Manual capture (authorize only)
- **PO Number Source:** Cart note (`order.note`)
- **Webhook Trigger:** [Shopwaive Action](https://apps.shopify.com/shopwaive-action)
  - Trigger: `Order Created`
  - Action: `POST to Flask webhook`

---

## ⚙️ Flask Webhook Server

- **Framework:** Flask
- **Hosting:** Azure App Service
- **Endpoint:** `/webhook`
- **Workflow:**
  1. Receive Shopify webhook with `order_id` and `po_number`
  2. Pull full order via Shopify Admin API
  3. Extract Level 2/3 fields
  4. Build `authCaptureTransaction` XML
  5. Send to Authorize.net sandbox

---

## 💳 Authorize.net Integration

- **Environment:** Sandbox
- **Endpoint:** `https://apitest.authorize.net/xml/v1/request.api`
- **Auth Type:** API Login ID + Transaction Key (env vars)
- **Transaction Type:** `authCaptureTransaction` (test mode)

### Level 2 Fields
- `invoiceNumber` (used as PO number)
- `tax.amount`
- `billTo.zip`

### Level 3 Fields
- `lineItems[].itemId`
- `lineItems[].name`
- `lineItems[].quantity`
- `lineItems[].unitPrice`
- `lineItems[].taxAmount`

---

## 🧪 Testing Notes

- Orders are created in Shopify with test cards
- Shopify processes authorization only (in production gateway test mode)
- Flask simulates `authCaptureTransaction` independently to sandbox
- Level 2 & 3 XML logs confirmed working
- Authorize.net sandbox confirms receipt of itemized order data and tax

---

## 🔜 Next Steps

- [ ] Switch to `priorAuthCaptureTransaction` in production
- [ ] Retrieve Authorize.net transaction ID from Shopify admin (or merchant interface)
- [ ] Match and capture using transaction ID + Level 2/3 XML
- [ ] Add logging & retry logic in Flask app
- [ ] Optional: Store logs in SQLite or Azure Table Storage

---

## 📁 Repository Integration

You can use this file as a `README.md` in a dedicated GitHub repository to document your workflow, share with collaborators, or guide production implementation.
