const COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com";
let latestPrices = { BTC: null, ETH: null, XRP: null };

// ✅ Detect if running in a browser
const isBrowser = typeof window !== "undefined";

// ✅ Use `ws` in Node.js, native `WebSocket` in browser
let WebSocketClient;
if (!isBrowser) {
  WebSocketClient = require("ws");
} else {
  WebSocketClient = window.WebSocket;
}

function connectToCoinbase() {
  const ws = new WebSocketClient(COINBASE_WS_URL);

  ws.onopen = () => {
    console.log("✅ Connected to Coinbase WebSocket");
    ws.send(
      JSON.stringify({
        type: "subscribe",
        channels: [{ name: "ticker", product_ids: ["BTC-USD", "ETH-USD", "XRP-USD"] }],
      })
    );
  };

  ws.onmessage = (event) => {
    try {
      const message = JSON.parse(event.data);
      if (message.type === "ticker") {
        if (message.product_id === "BTC-USD") latestPrices.BTC = parseFloat(message.price);
        if (message.product_id === "ETH-USD") latestPrices.ETH = parseFloat(message.price);
        // Uncomment for XRP
        if (message.product_id === "XRP-USD") latestPrices.XRP = parseFloat(message.price);
        // console.log(`📈 Updated Prices - BTC: $${latestPrices.BTC}, ETH: $${latestPrices.ETH}, XRP: $${latestPrices.XRP}`);
      }
    } catch (error) {
      console.error("🔥 WebSocket Parsing Error:", error);
    }
  };

  ws.onclose = () => {
    console.warn("🔄 WebSocket Disconnected. Reconnecting...");
    setTimeout(connectToCoinbase, 5000);
  };

  ws.onerror = (error) => {
    console.error("❌ WebSocket Error:", error);
  };
}

// ✅ Start WebSocket connection only on the client
if (isBrowser) {
  connectToCoinbase();
}

// ✅ Function to get the latest price
export function getLatestPrice(symbol) {
  return latestPrices[symbol] || null;
}
