type LogLevel = 'debug' | 'info' | 'warn' | 'error';

const LEVELS: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 };
const activeLevel: LogLevel = (process.env.LOG_LEVEL as LogLevel) ?? 'info';

/** Structured, leveled logger used across pages/modules/api instead of console.log. */
export class Logger {
  constructor(private readonly scope: string) {}

  private log(level: LogLevel, message: string, meta?: Record<string, unknown>) {
    if (LEVELS[level] < LEVELS[activeLevel]) return;
    const line = `[${new Date().toISOString()}] [${level.toUpperCase()}] [${this.scope}] ${message}`;
    // eslint-disable-next-line no-console
    console.log(meta ? `${line} ${JSON.stringify(meta)}` : line);
  }

  debug(message: string, meta?: Record<string, unknown>) {
    this.log('debug', message, meta);
  }

  info(message: string, meta?: Record<string, unknown>) {
    this.log('info', message, meta);
  }

  warn(message: string, meta?: Record<string, unknown>) {
    this.log('warn', message, meta);
  }

  error(message: string, meta?: Record<string, unknown>) {
    this.log('error', message, meta);
  }
}