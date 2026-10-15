#!/usr/bin/env python3
"""
app_mvp.py — MVP spec + Expo/React Native code + RevenueCat scaffolding

WHAT: Given a scored app idea (from app_factory.top20), this module:
  STAGE 4  run_mvp(slug)   → writes MVP.md (screens, data model, monetization, 1-week plan)
  STAGE 5  run_code(slug)  → writes an Expo/React Native starter:
                               - App.tsx, screens, navigation
                               - RevenueCat paywall (react-native-purchases)
                               - products config to paste into revenuecat.com
                               - README with copy→Replit→run steps

WHY Expo: the user's flow is idea→code→paste into Replit→build mobile. Expo is the
fastest path to a real iOS+Android app from generated code, and RevenueCat is the
monetization layer the user already picked (revenuecat.com, account 007aether).

SAFETY: no RevenueCat API keys, no store creds — those go in the user's dashboard
and Replit secrets. Generated code uses placeholders (YOUR_RC_API_KEY) the user fills.

Usage:
    python app_mvp.py --slug focus-flow --mvp
    python app_mvp.py --slug focus-flow --code
"""

import json
import logging
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
APPS_DIR = BASE_DIR / "AppFactory" / "apps"
LOG_FILE = BASE_DIR / "AppFactory" / "factory_log.json"
ROUTER_URL = "http://127.0.0.1:11435"

logger = logging.getLogger("app_mvp")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(BASE_DIR / "data" / "logs" / "app_factory.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


def ask_router(prompt, system=None, max_tokens=3500, timeout=150):
    system = system or "You are a senior React Native + product engineer. Write concrete, working code and specs."
    messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
    try:
        data = json.dumps({"model": "aether-cloud", "messages": messages,
                           "max_tokens": max_tokens, "temperature": 0.6}).encode()
        req = urllib.request.Request(f"{ROUTER_URL}/v1/chat/completions", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"router error: {e}")
        return None


def load_top():
    top_file = BASE_DIR / "AppFactory" / "top20.json"
    if not top_file.exists():
        return []
    try:
        return json.loads(top_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def find_app(slug):
    for app in load_top():
        if app.get("slug") == slug:
            return app
    return None


def log_action(entry):
    log = []
    if LOG_FILE.exists():
        try:
            log = json.loads(LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            log = []
    log.append(entry)
    log = log[-100:]
    LOG_FILE.parent.mkdir(exist_ok=True)
    LOG_FILE.write_text(json.dumps(log, ensure_ascii=False, indent=1), encoding="utf-8")


# ── STAGE 4: MVP spec ────────────────────────────────────────────────
def run_mvp(slug):
    app = find_app(slug)
    if not app:
        return {"ok": False, "error": f"app not found: {slug}"}

    prompt = f"""Write a concise MVP spec for this mobile app:

Name: {app.get('name')}
Category: {app.get('category')}
Pitch: {app.get('pitch')}
Monetization: {app.get('monetization')}
Audience: {app.get('audience')}

Structure it as (markdown):
1. One-line value prop
2. Target user
3. Core screens (3-5, with what each shows)
4. Data model (simple entities/fields)
5. Monetization (free vs pro — what's behind the paywall)
6. 1-week build plan (day by day, React Native / Expo)
7. Success metric (what number = it's working)

Keep it tight and actionable. Solo-dev scope."""

    mvp = ask_router(prompt, max_tokens=2000)
    if not mvp:
        return {"ok": False, "error": "router failed"}

    app_dir = APPS_DIR / slug
    app_dir.mkdir(parents=True, exist_ok=True)
    (app_dir / "MVP.md").write_text(mvp, encoding="utf-8")
    log_action({"ts": datetime.now(timezone.utc).isoformat(), "stage": "mvp", "slug": slug})
    return {"ok": True, "slug": slug, "file": str(app_dir / "MVP.md")}


# ── STAGE 5: code (Expo + RevenueCat) ────────────────────────────────
REVENUECAT_PRODUCTS = """// RevenueCat products — paste into https://app.revenuecat.com
// Project: {app_name} (account: 007aether@gmail.com)
// Add these as Entitlement "pro" with two offerings: monthly + yearly.

export const RC_PRODUCTS = {{
  monthly: "pro_monthly",   // e.g. {slug}_pro_monthly
  yearly: "pro_yearly",     // e.g. {slug}_pro_yearly
}};

// In RevenueCat dashboard:
//   1. Products → create {slug}_pro_monthly, {slug}_pro_yearly
//   2. Entitlements → "pro" → attach both products
//   3. Offering → "default" → add monthly + yearly packages
//   4. API Keys → copy your public SDK key (iOS/Android) → set below:
export const RC_API_KEY = "YOUR_REVENUECAT_PUBLIC_SDK_KEY";
"""

PAYWALL_SCREEN = '''import React, {{ useState, useEffect }} from "react";
import {{ View, Text, TouchableOpacity, StyleSheet, ActivityIndicator, Alert }} from "react-native";
import Purchases from "react-native-purchases";
import {{ RC_API_KEY, RC_PRODUCTS }} from "../config/revenuecat";

// Call once at app start (e.g. in App.tsx)
export async function initPurchases() {{
  try {{
    await Purchases.configure({{ apiKey: RC_API_KEY }});
  }} catch (e) {{
    console.warn("RevenueCat init failed", e);
  }}
}}

// Check if user has "pro"
export async function isPro() {{
  try {{
    const info = await Purchases.getCustomerInfo();
    return !!info.entitlements.active["pro"];
  }} catch {{
    return false;
  }}
}}

export default function Paywall({{ onClose }}) {{
  const [loading, setLoading] = useState(false);
  const [offering, setOffering] = useState(null);

  useEffect(() => {{
    (async () => {{
      try {{
        const offerings = await Purchases.getOfferings();
        if (offerings.current) setOffering(offerings.current);
      }} catch (e) {{ console.warn(e); }}
    }})();
  }}, []);

  const purchase = async (pkg) => {{
    setLoading(true);
    try {{
      const {{ customerInfo }} = await Purchases.purchasePackage(pkg);
      if (customerInfo.entitlements.active["pro"]) {{
        Alert.alert("🎉", "Pro unlocked!");
        onClose && onClose();
      }}
    }} catch (e) {{
      if (!e.userCancelled) Alert.alert("خطأ", String(e.message || e));
    }} finally {{ setLoading(false); }}
  }};

  return (
    <View style={{s.modal}}>
      <View style={{s.card}}>
        <Text style={{s.title}}>{{app_title}} Pro</Text>
        <Text style={{s.sub}}>{{pro_pitch}}</Text>

        {{offering?.availablePackages?.map((pkg) => (
          <TouchableOpacity key={{pkg.identifier}} style={{s.btn}} onPress={{() => purchase(pkg)}} disabled={{loading}}>
            <Text style={{s.btnText}}>
              {{pkg.product.title}} — {{pkg.product.priceString}}
            </Text>
          </TouchableOpacity>
        ))}}

        <TouchableOpacity onPress={{onClose}} style={{s.later}}>
          <Text style={{s.laterText}}>لاحقاً</Text>
        </TouchableOpacity>
        {{loading && <ActivityIndicator style={{{{ marginTop: 12 }}}} />}}
      </View>
    </View>
  );
}}

const s = StyleSheet.create({{
  modal: {{ flex: 1, backgroundColor: "rgba(0,0,0,0.5)", justifyContent: "center", padding: 24 }},
  card: {{ backgroundColor: "#fff", borderRadius: 20, padding: 24 }},
  title: {{ fontSize: 24, fontWeight: "800", marginBottom: 6 }},
  sub: {{ fontSize: 14, color: "#666", marginBottom: 20 }},
  btn: {{ backgroundColor: "#4F46E5", padding: 16, borderRadius: 12, marginBottom: 10, alignItems: "center" }},
  btnText: {{ color: "#fff", fontWeight: "700" }},
  later: {{ alignItems: "center", padding: 12 }},
  laterText: {{ color: "#999" }},
}});
'''

APP_TSX = '''import React, {{ useState, useEffect }} from "react";
import {{ SafeAreaView, View, Text, TouchableOpacity, StyleSheet, ScrollView }} from "react-native";
import {{ NavigationContainer }} from "@react-navigation/native";
import {{ createNativeStackNavigator }} from "@react-navigation/native-stack";
import Paywall, {{ initPurchases, isPro }} from "./screens/Paywall";

const Stack = createNativeStackNavigator();

function HomeScreen({{ navigation }}) {{
  const [pro, setPro] = useState(false);
  useEffect(() => {{ isPro().then(setPro); }}, []);

  return (
    <SafeAreaView style={{s.root}}>
      <ScrollView contentContainerStyle={{{{ padding: 24 }}}}>
        <Text style={{s.h1}}>{app_name}</Text>
        <Text style={{s.sub}>{pitch}</Text>

        <View style={{{{ marginTop: 24 }}}}>
          {{screens_placeholder}}
        </View>

        {{!pro && (
          <TouchableOpacity style={{s.proBtn}} onPress={{() => navigation.navigate("Paywall")}}>
            <Text style={{s.proBtnText}}>🔓 {pro_cta}</Text>
          </TouchableOpacity>
        )}}
      </ScrollView>
    </SafeAreaView>
  );
}}

export default function App() {{
  useEffect(() => {{ initPurchases(); }}, []);
  return (
    <NavigationContainer>
      <Stack.Navigator>
        <Stack.Screen name="Home" component={{HomeScreen}} />
        <Stack.Screen name="Paywall" component={{Paywall}} options={{{{ presentation: "modal" }}}} />
      </Stack.Navigator>
    </NavigationContainer>
  );
}}

const s = StyleSheet.create({{
  root: {{ flex: 1, backgroundColor: "#0B0F1A" }},
  h1: {{ fontSize: 28, fontWeight: "800", color: "#fff" }},
  sub: {{ color: "#9AA4B2", marginTop: 6 }},
  card: {{ backgroundColor: "#151B2B", padding: 16, borderRadius: 14, marginBottom: 12 }},
  proBtn: {{ backgroundColor: "#4F46E5", padding: 16, borderRadius: 12, marginTop: 20, alignItems: "center" }},
  proBtnText: {{ color: "#fff", fontWeight: "700" }},
}});
'''

README = """# {app_name}

> MVP جاهز — مولّد من EsprieAether App Factory
> الفكرة: {pitch}

## 🚀 كيفاش تخدم بيه (Replit)

### 1. Replit
1. افتح https://replit.com → **Create Repl** → **Import from GitHub** أو blank
2. ارفع هاد الملفات كلها (App.tsx, screens/, config/, package.json)
3. Replit كيتعرّف على Expo تلقائياً

### 2. RevenueCat (المونيتيزاسيون)
1. روح https://app.revenuecat.com (دخل بـ 007aether@gmail.com)
2. **Projects → New Project** → "{app_name}"
3. **Products** → زيد:
   - `{slug}_pro_monthly`
   - `{slug}_pro_yearly`
4. **Entitlements** → `pro` → ربط المنتجَين
5. **Offering** → `default` → ربط monthly + yearly
6. **API Keys** → copy الـ public SDK key
7. حطّو فـ `config/revenuecat.ts` → `RC_API_KEY`

### 3. شغّل
```bash
npm install
npx expo start
```
افحصل على Expo Go فالتيليفون → scan → التطبيق خدام 📱

### 4. Publish (App Store / Play)
- Expo EAS: `eas build --platform all`
- RevenueCat كيتتبّع الاشتراكات تلقائياً من Replit dashboard

## 💰 المونيتيزاسيون
{monetization}

## 🎯 الجمهور
{audience}

---
مولّد من **EsprieAether App Factory** — idea→score→MVP→code→RevenueCat
"""

PACKAGE_JSON = """{{
  "name": "{slug}",
  "version": "1.0.0",
  "main": "node_modules/expo/AppEntry.js",
  "scripts": {{
    "start": "expo start",
    "android": "expo start --android",
    "ios": "expo start --ios",
    "web": "expo start --web"
  }},
  "dependencies": {{
    "expo": "~51.0.0",
    "react": "18.2.0",
    "react-native": "0.74.5",
    "react-native-purchases": "^7.0.0",
    "@react-navigation/native": "^6.1.0",
    "@react-navigation/native-stack": "^6.9.0",
    "react-native-screens": "~3.31.1",
    "react-native-safe-area-context": "4.10.5"
  }},
  "devDependencies": {{
    "@babel/core": "^7.24.0",
    "@types/react": "~18.2.0",
    "typescript": "^5.3.0"
  }},
  "private": true
}}
"""


def run_code(slug):
    app = find_app(slug)
    if not app:
        return {"ok": False, "error": f"app not found: {slug}"}

    app_dir = APPS_DIR / slug
    (app_dir / "screens").mkdir(parents=True, exist_ok=True)
    (app_dir / "config").mkdir(parents=True, exist_ok=True)

    name = app.get("name", slug)
    pitch = app.get("pitch", "")

    # generate screen content from router (rich, app-specific)
    prompt = f"""Write the MAIN SCREEN content for a React Native app:
Name: {name}
Pitch: {pitch}
Category: {app.get('category')}

Give me:
1. A `pro_cta` string (Arabic, e.g. "افتح النسخة الكاملة") — the paywall button label
2. A `pro_pitch` string (Arabic) — what the pro version unlocks
3. A `screens_jsx` string — 2-3 starter <View style={{s.card}}> blocks with a Text title + Text body each, showing the app's core UI. Real content, not lorem. Use `s.card` style. Keep it valid JSX inside the array.

Respond ONLY as JSON:
{{"pro_cta": "...", "pro_pitch": "...", "screens_jsx": "..."}}"""

    extra = ask_router(prompt, max_tokens=1500, timeout=120)
    pro_cta = "افتح النسخة الكاملة"
    pro_pitch = "ميزات كاملة بلا حدود"
    screens_jsx = '        <View style={s.card}><Text style={s.h2}>ميزة 1</Text><Text style={s.body}>وصف الميزة</Text></View>'
    if extra:
        try:
            m = extra[extra.find("{"):extra.rfind("}") + 1]
            d = json.loads(m)
            pro_cta = d.get("pro_cta", pro_cta)
            pro_pitch = d.get("pro_pitch", pro_pitch)
            screens_jsx = d.get("screens_jsx", screens_jsx)
        except Exception:
            pass

    # ── write files ──
    # package.json
    (app_dir / "package.json").write_text(
        PACKAGE_JSON.format(slug=slug), encoding="utf-8")

    # config/revenuecat.ts
    (app_dir / "config" / "revenuecat.ts").write_text(
        REVENUECAT_PRODUCTS.format(app_name=name, slug=slug), encoding="utf-8")

    # App.tsx
    app_tsx = (APP_TSX
               .replace("{app_name}", name)
               .replace("{pitch}", pitch)
               .replace("{pro_cta}", pro_cta)
               .replace("{screens_placeholder}", screens_jsx))
    # un-escape the double-brace style objects we wrote as {{ }}
    app_tsx = app_tsx.replace("{{", "{").replace("}}", "}")
    (app_dir / "App.tsx").write_text(app_tsx, encoding="utf-8")

    # screens/Paywall.tsx
    paywall = (PAYWALL_SCREEN
               .replace("{app_title}", name)
               .replace("{pro_pitch}", pro_pitch)
               .replace("{{", "{").replace("}}", "}"))
    (app_dir / "screens" / "Paywall.tsx").write_text(paywall, encoding="utf-8")

    # README
    (app_dir / "README.md").write_text(README.format(
        app_name=name, pitch=pitch, slug=slug,
        monetization=app.get("monetization", ""),
        audience=app.get("audience", "")), encoding="utf-8")

    files = ["App.tsx", "screens/Paywall.tsx", "config/revenuecat.ts",
             "package.json", "README.md", "MVP.md"]
    log_action({"ts": datetime.now(timezone.utc).isoformat(), "stage": "code",
                "slug": slug, "files": files})
    return {"ok": True, "slug": slug, "dir": str(app_dir), "files": files}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--slug", required=True)
    ap.add_argument("--mvp", action="store_true")
    ap.add_argument("--code", action="store_true")
    args = ap.parse_args()
    if args.mvp:
        r = run_mvp(args.slug)
    else:
        r = run_code(args.slug)
    print(json.dumps(r, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
