from quart import (
    Quart, websocket, request, abort, render_template_string, Websocket
)
from quart_cors import cors
import stripe
import os
import logging
from typing import Any, Dict, Optional, Set


class Notifier:
    """
    A class to manage websocket clients and send notifications.
    """

    def __init__(self) -> None:
        """
        Initializes the Notifier with an empty set of clients.
        """
        self.clients: Set[Websocket] = set()

    async def register(self, ws: Websocket) -> None:
        """
        Registers a new websocket client and keeps the connection open
        to send messages.

        Args:
            ws (Websocket): The websocket object to register.
        """
        self.clients.add(ws._get_current_object())  # type: ignore
        try:
            while True:
                await ws.send("Connected")
                # Keep the connection open
                await ws.receive()
        except Exception:
            pass
        finally:
            self.clients.remove(ws._get_current_object())  # type: ignore

    async def notify_clients(self, message: str) -> None:
        """
        Sends a message to all registered websocket clients.

        Args:
            message (str): The message to send to the clients.
        """
        for client in self.clients:
            await client.send(message)


notifier = Notifier()

app: Quart = Quart(__name__)
app = cors(app, allow_origin="*")

# Setup logging
logging.basicConfig(level=logging.INFO)
logger: logging.Logger = logging.getLogger(__name__)

stripe.api_key = os.getenv('STRIPE_API_KEY', 'your_stripe_secret_key')
endpoint_secret: str = os.getenv(
    'STRIPE_WEBHOOK_SECRET', 'your_endpoint_secret')


@app.route("/")
async def home() -> str:
    """
    Renders the home page.

    Returns:
        str: The HTML content of the home page.
    """
    return await render_template_string(INDEX_HTML)


@app.route('/api/webhook', methods=['POST'])
async def webhook() -> tuple[str, int]:
    """
    Handles incoming webhook events from Stripe in an async manner.

    Returns:
        tuple: A response tuple containing the message and HTTP status code.
    """
    payload: str = await request.get_data(as_text=True)
    sig_header: Optional[str] = request.headers.get('Stripe-Signature')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logger.error(f'Invalid payload: {e}')
        abort(400)
    except stripe.error.SignatureVerificationError as e:  # type: ignore
        logger.error(f'Invalid signature: {e}')
        abort(400)

    # Handle the event
    if event['type'] == 'invoice.payment_succeeded':
        invoice: Dict[str, Any] = event['data']['object']
        await handle_payment_success(invoice)
    elif event['type'] == 'charge.refunded':
        refund: Dict[str, Any] = event['data']['object']
        await handle_refund(refund)
    else:
        logger.error(f'Unhandled event type: {event["type"]}')
        abort(400)

    return 'Success', 200


async def handle_payment_success(invoice: Dict[str, Any]) -> None:
    """
    Handles successful invoice payments.

    Args:
        invoice (Dict[str, Any]): The invoice data.
    """
    logger.info(f'Invoice {invoice["id"]} payment succeeded.')
    # Logic to handle successful invoice payment
    await notify_clients(f"Invoice {invoice['id']} payment succeeded")


async def handle_refund(refund: Dict[str, Any]) -> None:
    """
    Handles refunded charges.

    Args:
        refund (Dict[str, Any]): The refund data.
    """
    logger.info(f'Refund processed for {refund["id"]}.')
    # Logic to handle refund
    await notify_clients(f"Refund processed for {refund['id']}")


@app.websocket('/ws')
async def ws() -> None:
    """
    Registers a websocket connection.
    """
    await notifier.register(websocket)


async def notify_clients(message: str) -> None:
    """
    Sends a notification message to all clients.

    Args:
        message (str): The message to be sent.
    """
    await notifier.notify_clients(message)


if __name__ == '__main__':
    app.run()

INDEX_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Real-time Invoice Updates</title>
</head>
<body>
    <h1>Real-time Invoice Updates</h1>
    <div id="messages"></div>

    <script>
        let socket;

        function connectWebSocket() {
            socket = new WebSocket('ws://localhost:5000/ws');

            socket.onopen = function(event) {
                console.log('WebSocket connection established');
            };

            socket.onmessage = function(event) {
                const message = event.data;
                const timestamp = new Date().toLocaleTimeString();
                displayMessage(`${timestamp}: ${message}`);
            };

            socket.onclose = function(event) {
                console.log('WebSocket connection closed');
                const timestamp = new Date().toLocaleTimeString();
                displayMessage(`${timestamp}: WebSocket connection closed`);
                // Attempt to reconnect after 5 seconds
                setTimeout(connectWebSocket, 5000);
            };
        }

        function displayMessage(message) {
            const messagesDiv = document.getElementById('messages');
            const messageElement = document.createElement('p');
            messageElement.textContent = message;
            // Insert the new message at the top
            messagesDiv.insertBefore(messageElement, messagesDiv.firstChild);
        }

        // Initial connection attempt
        connectWebSocket();
    </script>
</body>
</html>
"""
