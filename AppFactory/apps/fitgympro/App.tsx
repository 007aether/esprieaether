import React, { useState, useEffect } from "react";
import { SafeAreaView, View, Text, TouchableOpacity, StyleSheet, ScrollView } from "react-native";
import { NavigationContainer } from "@react-navigation/native";
import { createNativeStackNavigator } from "@react-navigation/native-stack";
import Paywall, { initPurchases, isPro } from "./screens/Paywall";

const Stack = createNativeStackNavigator();

function HomeScreen({ navigation }) {
  const [pro, setPro] = useState(false);
  useEffect(() => { isPro().then(setPro); }, []);

  return (
    <SafeAreaView style={s.root}>
      <ScrollView contentContainerStyle={{ padding: 24 }}>
        <Text style={s.h1}>FitGymPro</Text>
        <Text style={s.sub}>AI-generated workout plans & progress tracking</Text>

        <View style={{ marginTop: 24 }}>
          {[
    <View style={s.card}> 
        <Text style={s.title}>إنشاء خطة تدريبية</Text> 
        <Text style={s.body}>أدخل التفاصيل الخاصة بك واختر نوع التدريب الذي ترغب في القيام به</Text> 
    </View>,
    <View style={s.card}> 
        <Text style={s.title}>متابعة التقدم</Text> 
        <Text style={s.body}>اطّلع على تقدمك في التدريب وأي تغييرات ترغب في تطبيقها على خطة التدريب</Text> 
    </View>
]}
        </View>

        {!pro && (
          <TouchableOpacity style={s.proBtn} onPress={() => navigation.navigate("Paywall")}>
            <Text style={s.proBtnText}>🔓 فتح النسخة الكاملة</Text>
          </TouchableOpacity>
        )}
      </ScrollView>
    </SafeAreaView>
  );
}

export default function App() {
  useEffect(() => { initPurchases(); }, []);
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="Paywall" component={Paywall} options={{ presentation: "modal" }} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}

const s = StyleSheet.create({
  root: { flex: 1, backgroundColor: "#0B0F1A" },
  h1: { fontSize: 28, fontWeight: "800", color: "#fff" },
  sub: { color: "#9AA4B2", marginTop: 6 },
  card: { backgroundColor: "#151B2B", padding: 16, borderRadius: 14, marginBottom: 12 },
  proBtn: { backgroundColor: "#4F46E5", padding: 16, borderRadius: 12, marginTop: 20, alignItems: "center" },
  proBtnText: { color: "#fff", fontWeight: "700" },
});
