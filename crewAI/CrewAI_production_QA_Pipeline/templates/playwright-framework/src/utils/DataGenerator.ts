/** Lightweight random test-data generation — no external faker dependency. */
export class DataGenerator {
  static randomEmail(prefix = 'qa'): string {
    return `${prefix}.${Date.now()}.${Math.floor(Math.random() * 1e5)}@example.com`;
  }

  static randomString(length = 8): string {
    const chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    return Array.from({ length }, () => chars[Math.floor(Math.random() * chars.length)]).join('');
  }

  static randomPhone(): string {
    return `+1${Math.floor(1_000_000_000 + Math.random() * 8_999_999_999)}`;
  }

  static randomInt(min: number, max: number): number {
    return Math.floor(Math.random() * (max - min + 1)) + min;
  }
}