"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ref, onValue, get } from "firebase/database";
import { db } from "../../../../firebaseClient";
import { auth } from "../../../../firebaseClient"; // ✅ Import Firebase Auth

export default function TradeHistory() {
  const params = useParams();
  const router = useRouter();
  const botId = params.botId;
  const [trades, setTrades] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const currentUser = auth.currentUser;
    if (!currentUser) {
      console.log("❌ No authenticated user found.");
      setError("You must be logged in to view trade history.");
      setLoading(false);
      return;
    }

    console.log(`✅ Authenticated as: ${currentUser.uid}`);

    if (!botId) {
      console.log("❌ No botId found.");
      return;
    }

    console.log(`✅ Fetching trade history for botId: ${botId}`);

    const userBotsRef = ref(db, `bots/${currentUser.uid}/${botId}/trades`);

    get(userBotsRef)
      .then((snapshot) => {
        const data = snapshot.val();
        console.log("📢 Firebase Response for Trades:", data);

        if (data) {
          const tradesArray = Object.entries(data).map(([tradeId, tradeData]) => ({
            id: tradeId,
            ...tradeData,
          }));
          setTrades(tradesArray.reverse()); // Show latest trades first
        } else {
          console.log("❌ No trade history found.");
          setTrades([]);
        }
        setLoading(false);
      })
      .catch((error) => {
        console.error("🔥 Firebase Error:", error);
        setError("Failed to load trade history. Check permissions.");
        setLoading(false);
      });
  }, [botId]);

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-3xl mx-auto bg-white p-8 rounded shadow">
        <h1 className="text-3xl font-bold mb-6 text-gray-800">Trade History</h1>
        <button
          onClick={() => router.back()}
          className="mb-4 px-4 py-2 bg-gray-500 text-white rounded hover:bg-gray-600"
        >
          ← Back to Bot List
        </button>

        {loading ? (
          <p className="text-gray-600">Loading trade history...</p>
        ) : error ? (
          <p className="text-red-500">{error}</p>
        ) : trades.length === 0 ? (
          <p className="text-gray-600">No trade history available.</p>
        ) : (
          <table className="w-full border-collapse border border-gray-200">
            <thead className="bg-gray-100">
              <tr>
                <th className="border border-gray-300 p-2">Trade ID</th>
                <th className="border border-gray-300 p-2">Type</th>
                <th className="border border-gray-300 p-2">Amount</th>
                <th className="border border-gray-300 p-2">Price</th>
                <th className="border border-gray-300 p-2">Time</th>
              </tr>
            </thead>
            <tbody>
              {trades.map((trade) => (
                <tr key={trade.id} className="text-center">
                  <td className="border border-gray-300 p-2">{trade.id}</td>
                  <td className={`border border-gray-300 p-2 ${trade.side === "buy" ? "text-green-600" : "text-red-600"}`}>
                    {trade.side.toUpperCase()}
                  </td>
                  <td className="border border-gray-300 p-2">{trade.amount}</td>
                  <td className="border border-gray-300 p-2">${trade.price}</td>
                  <td className="border border-gray-300 p-2">
                    {new Date(trade.time).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
