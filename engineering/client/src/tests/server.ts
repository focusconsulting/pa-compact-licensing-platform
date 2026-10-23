import { setupServer } from "msw/node";

import { handlers } from "src/api/mocks";

/** The generated API mocks for tests; override one with `server.use(...)`. */
export const server = setupServer(...handlers);
