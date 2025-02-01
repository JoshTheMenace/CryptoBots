import { NextResponse } from "next/server";
import { adminDb } from "../../../../../firebaseAdmin";
import axios from "axios"; // ✅ Use Axios to fetch market price

const COINBASE_API_URL = "https://api.coinbase.com/v2/prices";

async function fetchMarketPrice(symbol) {
  try {
    const response = await axios.get(`${COINBASE_API_URL}/${symbol}-USD/spot`);
    return parseFloat(response.data.data.amount);
  } catch (error) {
    console.error("❌ Error fetching market price:", error);
    return null;
  }
}

export async function POST(request, context) {
  try {
    // ✅ Explicitly await params (Next.js requires this for API routes)
    const params = await context.params;
    const botId = params.botId;

    // ✅ Parse request body
    let { side, amount, price, userId, symbol, orderType } = await request.json();

    if (!botId || !side || !amount || !symbol || !userId) {
      return NextResponse.json({ error: "Missing fields" }, { status: 400 });
    }

    // ✅ Fetch real-time price directly from Coinbase
    const marketPrice = await fetchMarketPrice(symbol);
    if (!marketPrice) {
      return NextResponse.json({ error: "Market price unavailable. Try again later." }, { status: 500 });
    }

    // ✅ Use market price if it's a market order
    if (orderType === "market") {
      price = marketPrice;
    }

    // ✅ Limit order: only execute if conditions are met
    if (orderType === "limit") {
      if ((side === "buy" && marketPrice > price) || (side === "sell" && marketPrice < price)) {
        return NextResponse.json({ error: "Limit order conditions not met." }, { status: 400 });
      }
    }

    // ✅ Get bot's current balances
    const botRef = adminDb.ref(`bots/${userId}/${botId}/balances`);
    const botSnapshot = await botRef.once("value");
    const botBalances = botSnapshot.val() || { USD: 0.0, BTC: 0.0, ETH: 0.0 };

    // ✅ Process trade
    if (side === "buy") {
      const totalCost = amount * price;
      if (botBalances.USD < totalCost) {
        return NextResponse.json({ error: "Insufficient bot USD balance" }, { status: 400 });
      }
      botBalances.USD -= totalCost; // ✅ Deduct from bot's USD balance
      botBalances[symbol] = (botBalances[symbol] || 0) + amount; // ✅ Increase asset balance
    } else if (side === "sell") {
      if ((botBalances[symbol] || 0) < amount) {
        return NextResponse.json({ error: `Insufficient ${symbol} balance` }, { status: 400 });
      }
      botBalances[symbol] -= amount; // ✅ Deduct from bot’s crypto balance
      botBalances.USD += amount * price; // ✅ Add USD balance to bot
    }

    // ✅ Save updated balances
    await Promise.all([
      botRef.set(botBalances),
      adminDb.ref(`bots/${userId}/${botId}/trades`).push({
        side,
        amount,
        price,
        symbol,
        orderType,
        marketPrice,
        time: Date.now(),
      }),
    ]);

    console.log(`✅ Trade Executed: ${side} ${amount} ${symbol} at $${price}`);
    return NextResponse.json({ success: true, balances: botBalances, executedPrice: price }, { status: 201 });
  } catch (error) {
    console.error("🔥 Error creating trade:", error);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
