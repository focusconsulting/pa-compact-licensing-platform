# Database Migrations Run at Container Startup

The API runs `yoyo-migrations` synchronously during the FastAPI lifespan startup
(`api/licensing_api/migrations.py`). Every time a new ECS task starts, it applies
any pending migrations before opening the connection pool and serving traffic.

## Implications for incompatible (breaking) schema changes

Because the migration runs inside the same deployment as the code that depends on it,
a breaking schema change (e.g. dropping a column, renaming a table, changing a type)
**must be shipped together with the code that handles the new schema**. The two cannot
be decoupled without a multi-step migration strategy.

### Deploying a breaking change

1. Write the migration SQL.
2. Update the application code to work with the new schema.
3. Deploy both together — the new container applies the migration on first startup,
   then immediately runs against the updated schema.

### Rolling back a breaking change

There is currently **no rollback mechanism**. `yoyo` tracks applied migrations and
will not re-run them. To undo a breaking change:

1. Write a **new** forward migration that reverses the schema change.
2. Update the application code to match the reverted schema.
3. Deploy both together as a new release.

Avoid using `yoyo`'s built-in rollback (`yoyo rollback`) in production — it is
unreliable for complex migrations and not wired into the startup path.

## Future consideration

For zero-downtime deployments with breaking schema changes, a three-phase
expand/contract pattern is recommended:

1. **Expand** — add new columns/tables, keep old ones. Deploy code that writes to both.
2. **Migrate** — backfill data if needed.
3. **Contract** — drop old columns/tables once all traffic uses the new schema.

This is not required today but worth adopting before the first production release.
