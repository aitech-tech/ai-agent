# Claude Desktop Skill Packaging

## What is a Claude Skill?

A Claude Skill is a directory containing a `SKILL.md` file with YAML frontmatter.
Claude Desktop reads this file to understand how to behave when working with a
specific set of tools or within a specific context.

The ReckLabs Narrator skill lives at:

```
.claude/skills/recklabs-narrator/SKILL.md
```

## Why the project root SKILL.md is not enough

A `SKILL.md` at the project root is a different concept — it documents the project
for Claude Code (the CLI), not Claude Desktop. Claude Desktop looks for skills in
specific configured skill directories, not in the project root automatically.

The skill in `.claude/skills/recklabs-narrator/SKILL.md` is the correct location
for the ReckLabs Narrator behavior instructions.

## How to use the skill with Claude Desktop

Claude Desktop does not auto-discover skills from arbitrary local directories.
Depending on the Claude Desktop version, you may need to:

1. **Upload the skill file directly in Claude Desktop** — use the skill upload
   feature (if available in your Claude Desktop version) to point to this directory.

2. **Reference the skill in your MCP config** — some Claude Desktop configurations
   allow specifying a skills directory path.

3. **Copy the content** — as a fallback, paste the contents of `SKILL.md` into
   your Claude Desktop system prompt or context window for the session.

## MCP still works without the skill

The MCP server exposes all `zb_` and `zoho_books_*` tools regardless of whether
Claude Desktop has loaded the skill. The skill only improves **tool selection** —
Claude will prefer `zb_` tools for reporting when the skill is active.

Without the skill, Claude may still use raw `zoho_books_list_*` tools for
reporting queries, which increases token usage and may hit context limits.

## Skill contents summary

The `recklabs-narrator` skill tells Claude to:

- Prefer `zb_` pre-processed tools for all reporting and analysis
- Not recalculate totals already returned by a report tool
- Use Indian rupee formatting as returned by the tool
- Only use `zoho_books_create_*`, `update_*`, and `delete_*` tools for write workflows
- Ask for confirmation before executing write operations

## YAML frontmatter format

```yaml
---
name: recklabs-narrator
description: Use when working with ReckLabs AI Agent MCP tools for Zoho Books reporting. Prefer zb_ pre-processed reporting tools for analysis/reporting and use raw zoho_books_ tools only for create/update/delete, authentication, or fallback.
---
```

The `description` field is the signal Claude Desktop uses to decide when to
activate the skill. It should describe the context clearly enough that Claude
activates it for Zoho Books reporting sessions.
