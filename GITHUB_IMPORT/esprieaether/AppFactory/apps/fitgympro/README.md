# FitGymPro

> MVP جاهز — مولّد من EsprieAether App Factory
> الفكرة: AI-generated workout plans & progress tracking

## 🚀 كيفاش تخدم بيه (Replit)

### 1. Replit
1. افتح https://replit.com → **Create Repl** → **Import from GitHub** أو blank
2. ارفع هاد الملفات كلها (App.tsx, screens/, config/, package.json)
3. Replit كيتعرّف على Expo تلقائياً

### 2. RevenueCat (المونيتيزاسيون)
1. روح https://app.revenuecat.com (دخل بـ 007aether@gmail.com)
2. **Projects → New Project** → "FitGymPro"
3. **Products** → زيد:
   - `fitgympro_pro_monthly`
   - `fitgympro_pro_yearly`
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
Advanced workout analysis and suggestions

## 🎯 الجمهور
Fitness professionals

---
مولّد من **EsprieAether App Factory** — idea→score→MVP→code→RevenueCat
