# claude-extensions

Personal [Claude Code plugin marketplace](https://docs.claude.com/en/docs/claude-code/plugins). A place to build, install, and experiment with plugins.

## Layout

```
.claude-plugin/marketplace.json   # marketplace manifest, lists all plugins
plugins/<name>/
  .claude-plugin/plugin.json       # plugin manifest
  hooks/        commands/  agents/  skills/   # whatever the plugin ships
```

## Use it

Add this marketplace, then install a plugin:

```
/plugin marketplace add /Users/sharat/Projects/claude-extensions
/plugin install response-format-hint@claude-extensions
```

(Or `/plugin marketplace add <git-url>` once pushed to a remote.)

## Plugins

| Plugin | What it does |
| --- | --- |
| `response-format-hint` | `UserPromptSubmit` hook that injects a response-format instruction — terse bullets prefixed with `[DONE]`, `[TODO LOW\|MEDIUM\|HIGH]`, `[INFO]`, or `[WARN]`. |

## Add a plugin

1. `mkdir -p plugins/<name>/.claude-plugin`
2. Write `plugins/<name>/.claude-plugin/plugin.json` (`name`, `version`, `description`).
3. Add its components (`hooks/hooks.json`, `commands/*.md`, `agents/*.md`, `skills/*`). Use `${CLAUDE_PLUGIN_ROOT}` for paths inside the plugin.
4. Register it in `.claude-plugin/marketplace.json` under `plugins`.
