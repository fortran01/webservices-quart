from quart import (Quart, render_template_string, Response,
                   abort, make_response, request)
from quart_cors import cors  # Added for CORS support
import asyncio
from typing import AsyncGenerator
from dataclasses import dataclass

app: Quart = Quart(__name__)
app = cors(app, allow_origin="*")  # Enable CORS for all domains

SSE_HTML: str = """
<!DOCTYPE html>
<html>
<head>
    <title>SSE Example</title>
    <script>
        if (!!window.EventSource) {
            var source;
            var reconnectAttempts = 0;
            var connect = function() {
                source = new EventSource('/events');

                source.onmessage = function(e) {
                    var dataElement = document.getElementById('data');
                    dataElement.innerHTML += e.data + '<br>';
                    reconnectAttempts = 0;
                    document.getElementById('reconnect-attempts').innerHTML =
                        'Reconnect attempts: ' + reconnectAttempts;
                };
                source.onerror = function(error) {
                    console.error("EventSource failed:", error);
                    source.close();
                    reconnectAttempts++;
                    document.getElementById('reconnect-attempts').innerHTML =
                        'Reconnect attempts: ' + reconnectAttempts;
                    setTimeout(connect, 5000);
                };
            };
            connect();
        } else {
            console.log("Browser doesn't support SSE. Consider upgrading.");
        }
    </script>
</head>
<body>
    <h1>Server Sent Events (SSE) Example</h1>
    <div id="data"></div>
    <div id="reconnect-attempts">Reconnect attempts: 0</div>
</body>
</html>
"""


@dataclass
class ServerSentEvent:
    data: str
    event: str | None = None
    id: int | None = None
    retry: int | None = None

    def encode(self) -> bytes:
        message = f"data: {self.data}"
        if self.event is not None:
            message = f"{message}\nevent: {self.event}"
        if self.id is not None:
            message = f"{message}\nid: {self.id}"
        if self.retry is not None:
            message = f"{message}\nretry: {self.retry}"
        message = f"{message}\r\n\r\n"
        return message.encode('utf-8')


@app.route('/')
async def index() -> str:
    """
    Renders the home page with an SSE example.

    Returns:
        str: The HTML content of the SSE example page.
    """
    return await render_template_string(SSE_HTML)


@app.route('/events')
async def sse_request() -> Response:
    """
    Handles server-sent event requests by streaming the event_stream generator.

    Returns:
        Response: A Quart Response object configured for server-sent events.
    """
    if "text/event-stream" not in request.headers.get("Accept", ""):
        abort(400)

    async def send_events() -> AsyncGenerator[bytes, None]:
        count: int = 0
        while True:
            await asyncio.sleep(1)  # Simulate a delay
            count += 1
            event = ServerSentEvent(data=f"{{'count': {count}}}", retry=10000)
            yield event.encode()

    response = await make_response(
        send_events(),
        {
            'Content-Type': 'text/event-stream',
            'Cache-Control': 'no-cache',
            'Transfer-Encoding': 'chunked',
        },
    )
    # Ensure the response is explicitly typed as Quart's Response
    assert isinstance(response, Response), \
        "Response object is not of type quart.wrappers.response.Response"
    return response

if __name__ == '__main__':
    app.run()
