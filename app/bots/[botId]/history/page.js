"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { ref, onValue, get } from "firebase/database";
import { db } from "../../../../firebaseClient";
import { auth } from "../../../../firebaseClient";

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
      setError("No bot ID provided.");
      setLoading(false);
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
          // Reverse so latest trades appear first
          setTrades(tradesArray.reverse());
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

  // ────────────────────────────────────────────────────────────────────────────────
  // RENDER
  // ────────────────────────────────────────────────────────────────────────────────
  return (
    <div className="min-h-screen bg-gradient-to-br from-purple-900 via-black to-gray-900 text-white p-6">
      <div className="max-w-3xl mx-auto bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl shadow-lg p-8">
        <h1 className="text-3xl font-bold mb-6">Trade History</h1>

        <button
          onClick={() => router.back()}
          className="mb-8 px-6 py-2 rounded-md font-semibold bg-gradient-to-r from-indigo-600 to-pink-600 
                     hover:from-indigo-500 hover:to-pink-500 transition-transform transform hover:scale-105 focus:outline-none"
        >
          ← Back to Bot List
        </button>

        {loading ? (
          <p className="text-center text-gray-300 animate-pulse">
            Loading trade history...
          </p>
        ) : error ? (
          <p className="text-center text-red-400 font-semibold">{error}</p>
        ) : trades.length === 0 ? (
          <p className="text-center text-gray-300">
            No trade history available.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full border-collapse text-left text-sm">
              {/* Table Head */}
              <thead>
                <tr className="bg-white/10 text-gray-200 uppercase text-xs tracking-wider">
                  <th className="px-4 py-3 border-b border-white/10">Trade ID</th>
                  <th className="px-4 py-3 border-b border-white/10">Type</th>
                  <th className="px-4 py-3 border-b border-white/10">Amount</th>
                  <th className="px-4 py-3 border-b border-white/10">Price</th>
                  <th className="px-4 py-3 border-b border-white/10">Time</th>
                </tr>
              </thead>

              {/* Table Body */}
              <tbody>
                {trades.map((trade) => {
                  const { id, side, amount, price, time } = trade;
                  const isBuy = side === "buy";

                  return (
                    <tr
                      key={id}
                      className="border-b border-white/10 hover:bg-white/10 transition"
                    >
                      <td className="px-4 py-3 text-gray-100 truncate">{id}</td>
                      <td
                        className={`px-4 py-3 font-semibold ${
                          isBuy ? "text-green-400" : "text-red-400"
                        }`}
                      >
                        {side.toUpperCase()}
                      </td>
                      <td className="px-4 py-3 text-gray-200">{amount}</td>
                      <td className="px-4 py-3 text-gray-200">${price}</td>
                      <td className="px-4 py-3 text-gray-200">
                        {new Date(time).toLocaleString()}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
