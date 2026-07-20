/**
 * Central config reader — every layer imports environment values from here
 * instead of touching process.env directly.
 */
export const config = {
  baseURL: process.env.BASE_URL ?? 'http://localhost:3000',
  apiBaseURL: process.env.API_BASE_URL ?? process.env.BASE_URL ?? 'http://localhost:3000',
  defaultTimeout: Number(process.env.DEFAULT_TIMEOUT ?? 10_000),
};