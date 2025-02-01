// coinbaseData.js
import WebSocket from "ws";

let latestPrices = { BTC: null, ETH: null, XRP: null };

function connectToCoinbase() {
  const COINBASE_WS_URL = "wss://ws-feed.exchange.coinbase.com";
  const ws = new WebSocket(COINBASE_WS_URL);

  ws.on("open", () => {
    console.log("✅ Connected to Coinbase WebSocket");
    ws.send(
      JSON.stringify({
        type: "subscribe",
        channels: [{ name: "ticker", product_ids: ["BTC-USD", "ETH-USD", "XRP-USD"] }],
      })
    );
  });

  ws.on("message", (data) => {
    try {
      const message = JSON.parse(data);
      console.log("📈 Received message:", message);
      if (message.type === "ticker") {
        if (message.product_id === "BTC-USD") {
          latestPrices.BTC = parseFloat(message.price);
          // console.log("Updated BTC:", latestPrices.BTC);
        } else if (message.product_id === "ETH-USD") {
          latestPrices.ETH = parseFloat(message.price);
          // console.log("Updated ETH:", latestPrices.ETH);
        } else if (message.product_id === "XRP-USD") {
          latestPrices.XRP = parseFloat(message.price);
          console.log("Updated XRP:", latestPrices.XRP); // Uncomment for XRP
        }
      }
    } catch (error) {
      console.error("🔥 WebSocket Parsing Error:", error);
    }
  });

  ws.on("close", () => {
    console.warn("🔄 WebSocket Disconnected. Reconnecting in 5 seconds...");
    setTimeout(connectToCoinbase, 5000);
  });

  ws.on("error", (error) => {
    console.error("❌ WebSocket Error:", error);
  });
}

// Ensure connection only starts once
if (!globalThis.coinbaseWSConnected) {
  connectToCoinbase();
  globalThis.coinbaseWSConnected = true;
}

export function getLatestPrices() {
  return latestPrices;
}
