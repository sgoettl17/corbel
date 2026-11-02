# Security

## Reporting a vulnerability

Open a private security advisory at https://github.com/sgoettl17/corbel/security/advisories/new. Please do not file public issues for vulnerabilities.

## Design

- **Read-only by default.** The create, update and delete tools are not registered unless the user sets `allow_writes` to `true`. They are annotated `destructiveHint: true`, so Claude asks before each call.
- **Fixed destinations.** Requests go only to the Procore API and login host for the configured environment. Callers pass an `operation_id` from the bundled index, never a URL, and all path values are URL-encoded.
- **HTTPS only.** The transport refuses non-HTTPS URLs.
- **Secrets.** The client ID and secret are declared `sensitive` in `plugin.json`, so Claude Code keeps them in the system credential store. They are passed to the server as environment variables, used only for the OAuth token request, and never logged or returned in tool output. Error text from Procore is truncated and never includes request credentials.
- **No dependencies.** The server uses only the Python standard library. No packages are downloaded at install or run time.
- **Output limits.** Tool results are truncated at 40,000 characters and pagination is capped at 10 pages.
- **Least privilege.** Corbel can only do what the Procore app's own permissions allow. Use a dedicated service account with the narrowest permissions you need.
