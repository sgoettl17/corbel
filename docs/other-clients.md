# Using Corbel with other MCP clients

Corbel is a plain stdio MCP server with no client-specific code.

## Cursor

Add to `~/.cursor/mcp.json` (or the project's `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "corbel": {
      "command": "python3",
      "args": ["/absolute/path/to/corbel/server/corbel_mcp.py"],
      "env": {
        "CORBEL_CLIENT_ID": "your-client-id",
        "CORBEL_CLIENT_SECRET": "your-client-secret",
        "CORBEL_COMPANY_ID": "your-company-id",
        "CORBEL_ENVIRONMENT": "sandbox"
      }
    }
  }
}
```

Prefer your client's secret-input feature over pasting secrets into a file. On Windows use `python` or `py` as the command if `python3` is not available.

## Any other client

Use the same command, args and environment variables. Optional: `CORBEL_ALLOW_WRITES=true` to expose create/update/delete, `CORBEL_ACCESS_TOKEN` to supply a token instead of client credentials.
