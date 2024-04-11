# webservices-quart

This project showcases an asynchronous web application built with Quart, integrating Stripe for payment processing and utilizing websockets for real-time notifications.

## Features

- **Stripe Payment Processing**: Handles Stripe payment processing asynchronously.
- **Stripe Webhook Handling**: Asynchronously receives and processes Stripe webhook events for payment success and refunds.
- **Real-time Notifications**: Utilizes websockets to send real-time notifications to clients upon payment success or refund.

## Setup

- Clone the repository
- Install dependencies:

```bash
pip install -r requirements.txt
```

## Running the Application

- Set the environment variables:

```bash
export STRIPE_SECRET_KEY=your_stripe_secret_key
export STRIPE_WEBHOOK_SECRET=your_stripe_webhook_secret
```

- Run the application:

```bash
python app.py
```

## Endpoints

- **Home Page**: `GET /` - Displays the real-time invoice updates page.
- **Stripe Webhook Handling**: `POST /api/webhook` - Handles Stripe webhook events for invoice payments and refunds.
- **WebSocket Connection**: `GET /ws` - Establishes a WebSocket connection for real-time updates.

## Real-time Updates

The home page includes a WebSocket client that connects to the server at `ws://localhost:5000/ws` to receive real-time updates about invoice payments and refunds.
