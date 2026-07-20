import { APIRequestContext, APIResponse } from '@playwright/test';
import { config } from '../config';
import { Logger } from './Logger';

const logger = new Logger('ApiHelper');

/** Thin wrapper around Playwright's APIRequestContext with retry + logging. */
export class ApiHelper {
  constructor(
    private readonly request: APIRequestContext,
    private readonly retries = 2,
  ) {}

  async get(path: string, options?: Parameters<APIRequestContext['get']>[1]): Promise<APIResponse> {
    return this.withRetry(() => this.request.get(`${config.apiBaseURL}${path}`, options), 'GET', path);
  }

  async post(path: string, options?: Parameters<APIRequestContext['post']>[1]): Promise<APIResponse> {
    return this.withRetry(() => this.request.post(`${config.apiBaseURL}${path}`, options), 'POST', path);
  }

  private async withRetry(fn: () => Promise<APIResponse>, method: string, path: string): Promise<APIResponse> {
    let lastError: unknown;
    for (let attempt = 1; attempt <= this.retries + 1; attempt++) {
      try {
        const response = await fn();
        logger.info(`${method} ${path} -> ${response.status()}`, { attempt });
        return response;
      } catch (error) {
        lastError = error;
        logger.warn(`${method} ${path} failed on attempt ${attempt}`, { error: String(error) });
      }
    }
    throw lastError;
  }
}