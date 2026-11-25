// RevenueCat products — paste into https://app.revenuecat.com
// Project: FitGymPro (account: 007aether@gmail.com)
// Add these as Entitlement "pro" with two offerings: monthly + yearly.

export const RC_PRODUCTS = {
  monthly: "pro_monthly",   // e.g. fitgympro_pro_monthly
  yearly: "pro_yearly",     // e.g. fitgympro_pro_yearly
};

// In RevenueCat dashboard:
//   1. Products → create fitgympro_pro_monthly, fitgympro_pro_yearly
//   2. Entitlements → "pro" → attach both products
//   3. Offering → "default" → add monthly + yearly packages
//   4. API Keys → copy your public SDK key (iOS/Android) → set below:
export const RC_API_KEY = "YOUR_REVENUECAT_PUBLIC_SDK_KEY";
