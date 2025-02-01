"use client";
import React, { useEffect, useState } from "react";
import Chart from "react-apexcharts";
import { auth, db } from "../firebase";
import { onAuthStateChanged } from "firebase/auth";
import { ref, onValue } from "firebase/database";
import { useRouter } from "next/navigation";

export default function BotComparisonChart() {
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [botSummaries, setBotSummaries] = useState([]);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (!firebaseUser) {
        router.push("/");
      } else {
        setUser(firebaseUser);
      }
    });
    return () => unsubscribe();
  }, [router]);

  useEffect(() => {
    if (!user) return;
    const botsRef = ref(db, `bots/${user.uid}`);
    onValue(botsRef, (snapshot) => {
      const data = snapshot.val() || {};
      // Summarize each bot’s value (mock logic)
      const summaries = Object.entries(data).map(([botId, botData]) => {
        const trades = botData.trades ? Object.values(botData.trades) : [];
        // For example, let's just take last trade price as "currentValue"
        const lastTrade = trades[trades.length - 1];
        const currentValue = lastTrade ? lastTrade.price : 0;
        return { botId, name: botData.name, currentValue };
      });
      setBotSummaries(summaries);
    });
  }, [user]);

  // Use a bar chart comparing each bot's currentValue
  const options = {
    chart: { type: "bar" },
    xaxis: { categories: botSummaries.map((b) => b.name) },
  };

  const series = [
    {
      name: "Bot Value",
      data: botSummaries.map((b) => b.currentValue),
    },
  ];

  return (
    <div>
      <h2>Compare Bot Values</h2>
      <Chart options={options} series={series} type="bar" height={300} />
    </div>
  );
}
