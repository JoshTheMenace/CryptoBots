// app/api/market-data/route.js

import { NextResponse } from "next/server";
import { getLatestPrices } from "../../../coinbaseData"; // adjust the path if needed

async function fetchFallbackPrice(productId) {
  // e.g. productId: "BTC-USD" or "ETH-USD"
  try {
    const res = await fetch(`https://api.coinbase.com/v2/prices/${productId}/spot`);
    if (!res.ok) {
      throw new Error("Network response not ok");
    }
    const data = await res.json();
    return parseFloat(data.data.amount);
  } catch (error) {
    console.error(`❌ Error fetching fallback price for ${productId}:`, error);
    return null;
  }
}

export async function GET(request) {
  const data = getLatestPrices();

  // If both values are still null, use fallback
  if (data.BTC === null && data.ETH === null) {
    console.warn("Market data not yet available; using fallback from Coinbase REST API.");
    const fallbackBTC = await fetchFallbackPrice("BTC-USD");
    const fallbackETH = await fetchFallbackPrice("ETH-USD");
    return NextResponse.json({ BTC: fallbackBTC, ETH: fallbackETH });
  }
  
  return NextResponse.json(data);
}
