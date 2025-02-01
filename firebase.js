import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth } from "firebase/auth";
import { getDatabase } from "firebase/database";

// Your Firebase configuration
const firebaseConfig = {

  apiKey: "AIzaSyDRwcK9LW17pi6M4irqWeDZ1nQR4BUtZgw",

  authDomain: "cryptobots-7ae5a.firebaseapp.com",

  databaseURL: "https://cryptobots-7ae5a-default-rtdb.firebaseio.com",

  projectId: "cryptobots-7ae5a",

  storageBucket: "cryptobots-7ae5a.firebasestorage.app",

  messagingSenderId: "89436245521",

  appId: "1:89436245521:web:ff4ce06d78124853b22bb0"

};


// Ensure Firebase is only initialized once & only on the client
let app;
if (typeof window !== "undefined") {
  app = getApps().length ? getApp() : initializeApp(firebaseConfig);
}

export const auth = app ? getAuth(app) : null;
export const db = app ? getDatabase(app) : null;
