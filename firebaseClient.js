import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, createUserWithEmailAndPassword } from "firebase/auth";
import { getDatabase, ref, set } from "firebase/database";

// Firebase configuration
const firebaseConfig = {
  apiKey: "AIzaSyDRwcK9LW17pi6M4irqWeDZ1nQR4BUtZgw",
  authDomain: "cryptobots-7ae5a.firebaseapp.com",
  databaseURL: "https://cryptobots-7ae5a-default-rtdb.firebaseio.com",
  projectId: "cryptobots-7ae5a",
  storageBucket: "cryptobots-7ae5a.firebasestorage.app",
  messagingSenderId: "89436245521",
  appId: "1:89436245521:web:ff4ce06d78124853b22bb0"
};

// Prevent Firebase from initializing on the server
const app = typeof window !== "undefined" && getApps().length ? getApp() : initializeApp(firebaseConfig);
export const auth = typeof window !== "undefined" ? getAuth(app) : null;
export const db = typeof window !== "undefined" ? getDatabase(app) : null;

/**
 * ✅ Function to Sign Up a User & Set Initial Balance
 * This ensures every new user starts with a USD balance
 */
export async function signUpUser(email, password) {
  try {
    if (!auth || !db) {
      console.error("🔥 Firebase not initialized properly.");
      return null;
    }

    const userCredential = await createUserWithEmailAndPassword(auth, email, password);
    const user = userCredential.user;

    // ✅ Set initial USD balance for the user
    await set(ref(db, `users/${user.uid}`), {
      usdBalance: 10000.0 // Initial balance
    });

    console.log(`✅ New user created: ${user.uid} with $10,000 balance.`);
    return user;
  } catch (error) {
    console.error("🔥 Signup Error:", error);
    return null;
  }
}
