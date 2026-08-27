# Codex compatibility

## Phase 1: Marketplace and skills

The Codex integration is an additive layer. It leaves the Claude Code plugin
bundle and its existing assets unchanged.

| Surface | Codex status | Phase 1 handling |
| --- | --- | --- |
| `skills/` | Directly supported | `.codex-plugin/plugin.json` explicitly registers `./skills/`. |
| `scripts/` | Needs small changes | Scripts remain in the plugin archive, but invocations that use Claude-only environment variables need portable path resolution. |
| `agents/` | Needs an adapter | The Markdown files are Claude subagent definitions, not Codex agent TOML files. They are intentionally not registered in Phase 1. |
| `commands/` | Claude-only | Claude slash-command routing is not declared in the Codex manifest. Equivalent workflows remain discoverable through skills. |
| `hooks/` | Claude-only in this repository | The current Codex manifest does not declare hooks; Codex's current manifest validation rejects unsupported hook fields. |
| `.mcp.json` | Needs a Codex adapter | It is deliberately omitted from the manifest because it is an empty Claude-oriented opt-in configuration and no Codex-specific MCP dependency is required for the skills. |
| Claude tool references | Needs review | `Task`, `run_shell_command`, and other Claude-specific names must be mapped to Codex capabilities per skill before they are advertised as portable. |
| `${CLAUDE_PLUGIN_ROOT}` and `${CLAUDE_PLUGIN_DATA}` | Needs an adapter | Existing Claude variables are preserved. Phase 2 should add Codex-safe path resolution without changing Claude behavior. |

## Phase 2 candidates

1. Add portable path-resolution guidance for skills that invoke bundled scripts.
2. Convert selected `agents/*.md` definitions to supported Codex agent TOML files after reviewing their tool and state assumptions.
3. Replace or document Claude slash-command entry points as Codex skill prompts.
4. Add a Codex MCP adapter only for validated, configured integrations; do not auto-enable credentials or network connectors.
5. Reassess hooks only when Codex exposes a supported hook manifest field.
