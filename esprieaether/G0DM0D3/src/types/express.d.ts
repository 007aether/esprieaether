// Module augmentation for Express Request with G0DM0D3 custom properties
declare global {
  namespace Express {
    interface Request {
      apiKeyId?: string;
      tier?: string;
      tierConfig?: any;
    }
  }
}

export {};
