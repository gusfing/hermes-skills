---
name: skillseal-yampi-ecommerce
description: "Yampi e-commerce: checkout, funnels, upsell, cart recovery."
version: 1.0.0
author: Workloop
license: MIT
---

# Yampi E-Commerce Mastery

Comprehensive knowledge base and operational reference for the Yampi e-commerce platform. Yampi is a Brazilian platform that excels in checkout conversion optimization, offering both a full virtual store builder and a standalone transparent checkout solution compatible with external platforms like Shopify and WooCommerce.

## Platform Overview

Yampi is a Brazilian e-commerce platform focused on reducing purchase friction and maximizing conversion rates. Its core differentiator is the **transparent checkout**, a PCI-compliant checkout solution that keeps customers on the same domain without redirects to external payment pages. The platform supports two operational modes:

- **Virtual Store + Checkout**: Full storefront with responsive themes plus Yampi checkout.
- **Checkout Only**: Embed Yampi's transparent checkout on top of external stores (Shopify, WooCommerce, custom sites).

Business model: free tier available with per-transaction fees; paid subscription plans for advanced features.

## Core Feature: Transparent Checkout

The transparent checkout is Yampi's flagship feature, designed to eliminate friction in the final purchase step.

### Order Bump
Product suggestions shown alongside the checkout form. Customers can add complementary items with a single click, increasing average order value (AOV) before payment. Common bump strategies include extended warranties, accessories, consumables, and premium versions.

### 1-Click Upsell (Post-Purchase)
After the initial payment is processed, customers see an upsell offer that requires only one click to accept. The platform retains credit card data for the session, so customers do not re-enter payment details. This is distinct from pre-purchase order bumps -- it happens after the first transaction clears.

### Multi-Gateway Retry (Purchase Retry)
If a credit card is declined by the primary payment gateway, Yampi automatically retries the transaction through secondary gateways configured in the store. This cascading retry mechanism increases approval rates without manual intervention.

### Fast Purchase (Fast Checkout)
Returning customers benefit from auto-filled fields (name, CPF, address), reducing form fatigue and accelerating repeat purchases. Yampi stores customer profiles for recognized visitors.

### PCI DSS Compliance
The checkout carries PCI certification, meaning sensitive card data is handled securely. This reduces the store owner's compliance burden and protects against fraud and chargeback exposure.

## Payment Gateways and Methods

Yampi integrates with multiple Brazilian payment providers:

| Gateway      | Methods                                          |
|--------------|--------------------------------------------------|
| Mercado Pago | Credit/debit cards, PIX, boleto, installments    |
| PagSeguro    | Credit/debit cards, PIX, boleto                  |
| PayPal       | Digital wallet, credit cards                     |
| Stone        | Credit/debit cards, PIX                          |
| PagBrasil    | Credit/debit cards, PIX, boleto                  |
| Yampi Gateway| Native processing with competitive rates         |

Supported payment methods at checkout:
- Credit card (with installment options up to 12x)
- Debit card
- PIX (instant payment, and PIX parcelado / installments)
- Boleto bancario

## Sales Funnel Architecture

```
Traffic Source (Ads, Social, Organic)
  -> Landing Page / Product Page
    -> Add to Cart
      -> Checkout (with Order Bump)
        -> Payment Processing (Gateway selection, Retry logic)
          -> Thank-You Page
            -> Post-Purchase 1-Click Upsell
              -> Final Confirmation
```

### Funnel Configuration Best Practices

1. Position order bumps before payment, not after. Use a single checkbox or toggle.
2. Trigger the 1-click upsell immediately after the first payment succeeds.
3. Use the bump to show a bundle discount (e.g., "Add this item for 30% off").
4. Keep upsells below 60% of the original order value to avoid rejection.
5. Instrument every funnel stage with pixel events for retargeting.

## Abandoned Cart Recovery

### Native Recovery Funnel

Yampi provides a free, built-in abandoned cart recovery funnel with up to 4 message stages per abandoned cart. Configuration per stage:

- Channel: email or SMS (configurable per stage)
- Custom subject line and body text
- Coupon codes (different discount per stage)
- Customer name personalization
- Direct link to abandoned cart
- Stage-specific activation toggle

Recommended timing:
1. Stage 1 -- 30 minutes to 3 hours after abandonment (urgency, cart link)
2. Stage 2 -- 24 hours after abandonment (reminder, small coupon)
3. Stage 3 -- 48 hours after abandonment (urgency, higher-value coupon)
4. Stage 4 -- 72 hours after abandonment (last chance, best offer)

### WhatsApp Cart Recovery

Yampi has no native WhatsApp notification channel. WhatsApp integration must be implemented via:

1. **Webhook-based approach**: Point Yampi webhooks at a server that calls a WhatsApp Business API provider (Whapi.Cloud, Atualizap, WSUPP).
2. **No-code platforms**: Make.com (Integromat), n8n, or Zapier bridge Yampi webhooks to WhatsApp APIs.
3. **WhatsApp Business API providers**:
   - Whapi.Cloud: REST API, no per-message fee, HMAC-SHA256 validation
   - Atualizap: Purpose-built for Yampi, pre-built recovery flows
   - WSUPP: Dedicated cart recovery plus WhatsApp messaging

WhatsApp achieves approximately 98% open rates vs 20-25% for email, making it the highest-performing recovery channel in Brazil.

### Key Webhook Events for Recovery

- **cart.abandoned**: Customer added products, reached checkout, left without paying
- **order.created**: Order created but payment not yet confirmed
- **order.paid**: Payment confirmed
- **order.cancelled**: Payment failed or order was cancelled

## Pixel and Tracking Integrations

### Google Ads

Yampi sends three standard events automatically when the Google Ads conversion ID and label are configured:

| Event       | Trigger               | Available in           |
|-------------|-----------------------|------------------------|
| view_item   | Product page view     | Virtual Store          |
| add_to_cart | Product added to cart | Virtual Store          |
| purchase    | Order completed       | Both (Store+Checkout)  |

Data sent: order ID, total value, product IDs/names, quantities, conversion status.

### Facebook/Meta Pixel

Configured via Admin > Settings > Integrations > Meta Pixel. Events fired: PageView, ViewContent, AddToCart, InitiateCheckout, Purchase. Meta Conversions API (CAPI) can be layered on via server-side setup.

### TikTok Pixel

Installable through the Yampi admin panel. Standard e-commerce events forwarded.

### Google Analytics

Universal Analytics and GA4 supported via Measurement ID in the admin panel.

## Webhook System

Configuration: Admin > Settings > Webhooks.

### Event Types

| Event           | Description                                       |
|-----------------|---------------------------------------------------|
| order.created   | New order generated (before payment confirmation) |
| order.paid      | Payment successfully processed                    |
| order.updated   | Order data modified (status, shipping, etc.)      |
| order.cancelled | Order cancelled or payment failed                 |
| cart.abandoned  | Cart abandoned (requires cart tracking setup)     |
| product.created | Product added to catalog                          |
| product.updated | Product data modified                             |
| product.deleted | Product removed from catalog                      |

### Webhook Security

Webhooks include HMAC-SHA256 signature in the `X-Yampi-Signature` header. Validate by computing HMAC of the raw request body against the shared secret configured in the Yampi admin panel. Reject requests where the computed signature does not match.

### Common Webhook Consumers

- CRM/ERP: HubSpot, RD Station, ActiveCampaign, Conta Azul
- WhatsApp automation: Whapi.Cloud, Atualizap
- Anti-fraud: ClearSale
- Shipping: SuperFrete, Frenet
- Marketing automation: Albato, Pluga, n8n

## WhatsApp Integration Architecture

```
Yampi Store -> Webhook (order event) -> Integration Server -> WhatsApp API -> Customer
```

The integration server must:
1. Receive and validate Yampi webhooks (HMAC-SHA256)
2. Map event type to message template
3. Look up customer phone (ensure E.164 format: +55XXXXXXXXXXX)
4. Send message via chosen WhatsApp API provider
5. Respect LGPD opt-in requirements

### Message Lifecycle Coverage

1. Order confirmation (order.paid)
2. Payment failure recovery (order.cancelled)
3. Shipping updates (order.updated with tracking)
4. Delivery confirmation
5. Review/satisfaction request
6. Re-engagement and upsell

## Store Management

### Themes and Customization
- Responsive themes optimized for mobile (majority of Brazilian e-commerce traffic)
- Customizable colors, fonts, and layout elements
- Fast page load times by design

### Order and Inventory Management
- Full order lifecycle dashboard
- Real-time inventory synchronization
- Automated stock level updates after each purchase
- Multi-SKU variant support

## Integrations Ecosystem

### Anti-Fraud
ClearSale Total integration via webhook callback for transaction risk scoring.

### Shipping
SuperFrete (discounted rates, label generation), Frenet (multi-carrier freight), Correios, custom shipping tables and free shipping rules.

### Marketing Automation
ActiveCampaign, RD Station, HubSpot CRM, MailChimp via native or Albato/Pluga connectors.

### Checkout on External Platforms
Yampi transparent checkout embeds into WooCommerce (plugin), Shopify (script injection), and custom HTML sites.

## Pricing Structure

- Free plan with per-transaction fees
- Paid subscription plans scaling with features
- Transaction fees vary by gateway and plan level

## Optimization Checklist

### Checkout
- [ ] Transparent checkout enabled (not redirect-based)
- [ ] At least one order bump configured per product
- [ ] 1-click upsell activated with relevant offer
- [ ] Multi-gateway retry configured (2+ gateways)
- [ ] Fast purchase / auto-fill enabled
- [ ] PIX payment method available

### Funnel
- [ ] Pixel tracking active on all stages (Google, Meta, TikTok)
- [ ] Order bump shown with discount anchor
- [ ] Upsell capped below 60% of original order value

### Cart Recovery
- [ ] Native recovery funnel configured (all 4 stages)
- [ ] Stage 1 sends within 3 hours of abandonment
- [ ] Coupon codes escalate across stages
- [ ] WhatsApp recovery implemented via webhook + API provider
- [ ] Customer consent (LGPD) verified before WhatsApp messaging

### Integration Health
- [ ] Webhook endpoint operational and validating HMAC signatures
- [ ] All payment gateways returning healthy status
- [ ] Pixel events firing and verified via Tag Assistant
- [ ] ClearSale anti-fraud active for high-value transactions
- [ ] Shipping integrations returning real-time rates

## Common Pitfalls

1. **Declined card cascade not configured**: Without secondary gateways, a single decline means a lost sale. Always configure at least two payment gateways.
2. **No order bump**: The highest-ROI checkout feature; stores that skip it leave 15-30% uplift on the table.
3. **Email-only cart recovery**: Brazilian email open rates hover around 20%. Complement with WhatsApp for 5x better reach.
4. **Upsell too expensive**: Offers above 60% of the original order value typically convert poorly and erode trust.
5. **Webhook signature not validated**: Accepting unverified webhooks is a security risk; always validate HMAC-SHA256.
6. **LGPD non-compliance on WhatsApp**: Sending WhatsApp messages without opt-in violates Brazilian data protection law.
7. **No pixel deduplication**: Installing the same pixel via Yampi AND GTM simultaneously causes duplicate conversions.
