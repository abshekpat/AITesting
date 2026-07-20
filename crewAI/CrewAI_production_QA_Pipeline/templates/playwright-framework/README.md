# Advanced Playwright Framework

Enterprise-grade Playwright automation (Page Object Model + Module pattern),
scaffolded to match `docs/ARCHITECTURE.html`. Generated and kept up to date
by the CrewAI QA pipeline's Playwright Automation Engineer agent.

## Layers

- `src/pages`    — locators + basic UI actions only (Page Object Model)
- `src/modules`  — business-logic orchestration on top of pages
- `src/tests`    — test.describe/test specs, tagged (`@P0`, `@Login`, ...)
- `src/api`      — API client classes for API-level tests
- `src/utils`    — shared infra: Logger, WaitHelper, DataGenerator, ApiHelper
- `src/fixtures` — custom Playwright fixtures wiring pages + modules together
- `src/config`   — environment/config reader
- `src/testdata` — static JSON test data

## Quick start

1. `npm install`
2. Copy `.env.example` to `.env` and set `BASE_URL`
3. `npm test` — run all tests
4. `npm run test:p0` — run only `@P0` tagged tests
5. `npm run report` — open the HTML report

## Ownership

`playwright.config.ts`, `tsconfig.json`, `package.json`, `src/config/` and
`src/utils/` are shared infrastructure — do not duplicate them inside a
generated feature. Everything under `src/pages`, `src/modules`, `src/tests`,
`src/api` and `src/fixtures` is generated per feature/ticket.