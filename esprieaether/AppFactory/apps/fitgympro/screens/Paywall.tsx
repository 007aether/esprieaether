import React, { useState, useEffect } from "react";
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert } from "react-native";
import Purchases from "react-native-purchases";
import { RC_API_KEY, RC_PRODUCTS } from "../config/revenuecat";

// Call once at app start (e.g. in App.tsx)
export async function initPurchases() {
  try {
    await Purchases.configure({ apiKey: RC_API_KEY });
  } catch (e) {
    console.warn("RevenueCat init failed", e);
  }
}

// Check if user has "pro"
export async function isPro() {
  try {
    const info = await Purchases.getCustomerInfo();
    return !!info.entitlements.active["pro"];
  } catch {
    return false;
  }
}

export default function Paywall({ onClose }) {
  const [loading, setLoading] = useState(false);
  const [offering, setOffering] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const offerings = await Purchases.getOfferings();
        if (offerings.current) setOffering(offerings.current);
      } catch (e) { console.warn(e); }
    })();
  }, []);

  const purchase = async (pkg) => {
    setLoading(true);
    try {
      const { customerInfo } = await Purchases.purchasePackage(pkg);
      if (customerInfo.entitlements.active["pro"]) {
        Alert.alert("🎉", "Pro unlocked!");
        onClose && onClose();
      }
    } catch (e) {
      if (!e.userCancelled) Alert.alert("خطأ", String(e.message || e));
    } finally { setLoading(false); }
  };

  return (
    <View style={s.modal}>
      <View style={s.card}>
        <Text style={s.title}>{FitGymPro} Pro</Text>
        <Text style={s.sub}>{ unlock جميع الوظائف والخطط التدريبية المتقدمة وتحديثات البيانات الشخصية المتقدمة}</Text>

        {offering?.availablePackages?.map((pkg) => (
          <TouchableOpacity key={pkg.identifier} style={s.btn} onPress={() => purchase(pkg)} disabled={loading}>
            <Text style={s.btnText}>
              {pkg.product.title} — {pkg.product.priceString}
            </Text>
          </TouchableOpacity>
        ))}

        <TouchableOpacity onPress={onClose} style={s.later}>
          <Text style={s.laterText}>لاحقاً</Text>
        </TouchableOpacity>
        {loading && <ActivityIndicator style={{ marginTop: 12 }} />}
      </View>
    </View>
  );
}

const s = StyleSheet.create({
  modal: { flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "center", padding: 24 },
  card: { backgroundColor: "#fff", borderRadius: 20, padding: 24 },
  title: { fontSize: 24, fontWeight: "800", marginBottom: 6 },
  sub: { fontSize: 14, color: "#666", marginBottom: 20 },
  btn: { backgroundColor: "#4F46E5", padding: 16, borderRadius: 12, marginBottom: 10, alignItems: "center" },
  btnText: { color: "#fff", fontWeight: "700" },
  later: { alignItems: "center", padding: 12 },
  laterText: { color: "#999" },
});
