---
title: "I spent 2 hours making Claude auto-start remote-control. The fix was one JSON key."
slug: claude-remote-control-hidden-setting
tags: [claude-code, reverse-engineering, internals, devtools]
cover_image: null
canonical: hashnode
series: null
published: false
---

I use Claude Code from my phone constantly — walking, commuting, between meetings. The iOS app's `/remote-control` feature lets you control a running CLI session remotely, which is genuinely useful. But every time I open a new session, I have to type `/remote-control` manually before I can connect from the phone.

I wanted it to auto-start. Two hours later I had reverse-engineered the binary and the answer was a single line of JSON that isn't documented anywhere.

Here's what I tried and what actually works.

## Attempt 1: Run it as a daemon

`claude remote-control` is a separate CLI subcommand that's supposed to run as a headless bridge — exactly what I wanted. I set it up as a launchd daemon so it would start on boot.

It didn't work.

The daemon starts, registers an environment URL, and the iPhone can see the session. But when the iPhone spawns a conversation, the Mac spawns a child process and... nothing. The iPhone shows "Session started" and then silence. The child process is alive and healthy; it just never sends responses back.

This is a known upstream bug. The always-on headless path isn't ready yet.

**Dead end 1.**

## Attempt 2: SessionStart hook

Claude Code has a hooks system — you can run shell commands on events like session start. I wrote a hook to trigger `/remote-control` at startup.

Problem: `/remote-control` is a REPL slash command. It's processed inside the interactive UI, not the shell. There's no `claude --remote-control-on` flag you can fire from a shell hook. A shell hook can't reach into the running REPL and flip a UI toggle.

**Dead end 2.**

## Attempt 3: The `--remote-control` flag

There is actually a `--remote-control` / `--rc` CLI flag. I tried launching with it.

It worked sometimes. But it silently ignored itself when a blocker condition was present — no error, just no bridge. And even when it did work, there was no guarantee it'd fire on every session consistently.

**Dead end 2.5.**

## Into the binary

At this point I pulled up the Claude Code binary and started grepping strings.

`claude` ships as a single Mach-O arm64 binary (on macOS). Its JavaScript source is compiled and bundled in, and the string table is readable. I searched for `remoteControl`:

```
replBridgeEnabled
replBridgeExplicit
replBridgeConnected
replBridgeSessionActive
remoteControlAtStartup
remoteControlAtStartupSetting
```

That last one — `remoteControlAtStartupSetting` — is distinct from `replBridgeExplicit` (which is the "user explicitly typed `/remote-control` this session" flag). The name pattern suggests it's a persisted setting, not session state.

I cross-referenced with the startup logic. The bridge's initial enabled state is computed as:

```
replBridgeEnabled = explicitFlag || remoteControlAtStartupSetting || kairosEnabled
```

Where `kairosEnabled` is an internal Anthropic feature flag, and `remoteControlAtStartupSetting` is... a user-configurable boolean.

The question was where it's stored.

## The answer

Claude Code has two config files that people often confuse:

- `~/.claude/settings.json` — the settings file. Model preferences, hooks, permissions.
- `~/.claude.json` — the app state file. OAuth tokens, UI state, feature toggles.

The `remoteControlAtStartup` key lives in `~/.claude.json`. Not `settings.json`. This is why it's not in the docs under configuration — it's written by the in-app toggle ("Enable Remote Control for all sessions"), not by hand-editing settings.

The fix:

```json
// ~/.claude.json
{
  "remoteControlAtStartup": true
}
```

One key. Every interactive `claude` session now auto-starts with remote-control enabled. iPhone connects immediately with no manual setup.

## What's actually happening

When Claude Code starts, it reads `remoteControlAtStartup` from `~/.claude.json` and uses it as one of three positive triggers for the bridge. If it's true and no blocker condition fires (no CI token, no API-key-only auth, no org policy block), the bridge starts automatically.

The pointer file it writes — `~/.claude/remote/<dir-hash>/bridge-pointer.json` — is what the iOS app and statusline integrations read to detect an active bridge. It has a 4-hour TTL and gets cleared on teardown.

## The lesson

When a tool's behavior is undocumented, the binary string table is often faster than the GitHub issues. The internal variable names (`remoteControlAtStartupSetting`) were a direct map to the config key (`remoteControlAtStartup`). Five minutes of grepping saved me from filing an issue and waiting.

If you're using Claude Code and want the iOS app to connect without the manual `/remote-control` step — add that one key to `~/.claude.json`.
