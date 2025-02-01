export const dynamic = "force-dynamic"; // ✅ Ensures this API runs dynamically on every request

import { NextResponse } from "next/server";
import { getLatestPrices } from "../../../coinbaseData"; // Adjust path if needed

async function fetchFallbackPrice(productId) {
  try {
    const res = await fetch(`https://api.coinbase.com/v2/prices/${productId}/spot`, { cache: 'no-store' });
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

  // ✅ If both values are null, use fallback REST API
  if (data.BTC === null && data.ETH === null && data.XRP === null) {
    console.warn("Market data not yet available; using fallback from Coinbase REST API.");
    const fallbackBTC = await fetchFallbackPrice("BTC-USD");
    const fallbackETH = await fetchFallbackPrice("ETH-USD");
    const fallbackXRP = await fetchFallbackPrice("XRP-USD");

    return new NextResponse(
      JSON.stringify({ BTC: fallbackBTC, ETH: fallbackETH }),
      {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
          "Pragma": "no-cache",
          "Expires": "0",
        },
      }
    );
  }

  return new NextResponse(
    JSON.stringify(data),
    {
      status: 200,
      headers: {
        "Content-Type": "application/json",
        "Cache-Control": "no-store, no-cache, must-revalidate, proxy-revalidate",
        "Pragma": "no-cache",
        "Expires": "0",
      },
    }
  );
}
