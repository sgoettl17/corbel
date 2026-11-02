# Privacy

Corbel is a local program with no server of its own and no telemetry.

| Data | Where it goes | Retention |
| --- | --- | --- |
| Procore client ID and secret | Sent only to the Procore login host (`login.procore.com` or `login-sandbox.procore.com`) to get an access token | Held in memory while the server runs; stored by Claude Code in your system credential store |
| Procore access token | Sent only to the Procore API host (`api.procore.com` or `sandbox.procore.com`) | Held in memory only |
| API requests and responses | Between your machine and Procore; responses are then returned to your MCP client and its model | Not stored by Corbel |
| Company ID | Sent as the `Procore-Company-Id` header | Stored in your Claude Code settings |

Corbel does not read your conversation, files, memory or other tools. It makes no background requests. The author receives no data.

Procore data that your MCP client sends to a model is governed by that client's and model provider's privacy terms and by your Procore agreement.
