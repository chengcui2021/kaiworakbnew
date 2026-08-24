#!/usr/bin/env node
/**
 * PreToolUse gate (Edit|Write): deny code edits until every plugin this repo
 * declares in its checked-in `.claude/settings.json` `enabledPlugins` is
 * actually installed for THIS project (per ~/.claude/plugins/installed_plugins.json)
 * AND not disabled for this checkout (an `enabledPlugins: { "<key>": false }`
 * override in `.claude/settings.local.json` outranks the checked-in `true` and
 * unloads the plugin's hooks — so it must block edits too).
 *
 * This is the bootstrap guard the plugin itself cannot provide — an
 * uninstalled plugin can't run its own hooks — so the script is committed in
 * each consuming repo (`.claude/hooks/require-plugin.mjs`) and registered in
 * that repo's checked-in settings.json:
 *
 *   "hooks": { "PreToolUse": [ { "matcher": "Edit|Write", "hooks": [
 *     { "type": "command", "command": "node \"$CLAUDE_PROJECT_DIR/.claude/hooks/require-plugin.mjs\"" }
 *   ] } ] }
 *
 * Canonical copy lives in metamorphic-claude-conventions/bootstrap/. Keep
 * consumer copies in sync with it.
 *
 * Scope: only source files (ts/js/vue) under the frontend dir (`frontendDir`
 * in .claude/project.json, default "frontend"; "" = repo root) — docs and
 * backend work are never blocked. An install entry counts if it is user-scoped
 * or project-scoped to this repo; a project-scoped install for a *different*
 * repo does not load here, so it does not count.
 *
 * Missing installed_plugins.json = nothing installed = deny. Any unexpected
 * error = allow (a broken hook must never brick a session).
 */
import { readFileSync, writeFileSync, statSync, existsSync } from 'node:fs'
import { execFileSync } from 'node:child_process'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const CODE_FILE = /\.(ts|tsx|js|jsx|mjs|cjs|vue)$/

function projectDir() {
  return process.env.CLAUDE_PROJECT_DIR || process.cwd()
}

function configDir() {
  return process.env.CLAUDE_CONFIG_DIR || join(process.env.HOME || '', '.claude')
}

function readJson(path) {
  try {
    return JSON.parse(readFileSync(path, 'utf8'))
  } catch {
    return null
  }
}

/** Plugin keys ("name@marketplace") this repo's checked-in settings enable. */
function requiredPlugins(dir) {
  const enabled = readJson(join(dir, '.claude', 'settings.json'))?.enabledPlugins ?? {}
  return Object.keys(enabled).filter((k) => enabled[k] === true)
}

/**
 * True if `.claude/settings.local.json` overrides `key` to false. Local
 * settings outrank the checked-in settings.json, so this is the one layer
 * that can disable a repo-required plugin (user-level settings rank BELOW
 * the project file and cannot).
 */
function locallyDisabled(key, dir) {
  return readJson(join(dir, '.claude', 'settings.local.json'))?.enabledPlugins?.[key] === false
}

/** "frontend/" prefix from project.json, "" when the frontend is the repo root. */
function frontendPrefix(dir) {
  const cfg = readJson(join(dir, '.claude', 'project.json'))
  const sub = String(cfg?.frontendDir ?? 'frontend').replace(/^\.\/?$/, '')
  return sub ? `${sub}/` : ''
}

/** Install entries for `key` that apply to this repo (user-wide or project-scoped here). */
function installEntries(key, dir) {
  const registry = readJson(join(configDir(), 'plugins', 'installed_plugins.json'))
  const entries = registry?.plugins?.[key]
  if (!Array.isArray(entries)) return []
  return entries.filter(
    (e) => e?.scope === 'user' || (e?.scope === 'project' && e?.projectPath === dir)
  )
}

/**
 * When this session started, from the transcript file's creation time.
 * null (skip the loaded-check) when unavailable — e.g. no transcript_path in
 * the event, or a filesystem without birthtime.
 */
function sessionStartMs(event) {
  try {
    const path = event?.transcript_path
    if (!path || typeof path !== 'string') return null
    const t = statSync(path).birthtimeMs
    return t > 0 ? t : null
  } catch {
    return null
  }
}

/** True if every applicable install of the plugin happened after session start. */
function installedMidSession(entries, startMs) {
  if (startMs === null) return false
  return entries.every((e) => {
    const t = Date.parse(e?.installedAt ?? '')
    return !Number.isNaN(t) && t > startMs
  })
}

/** Repo root: CLAUDE_PROJECT_DIR, else walk up from this script, else cwd. */
function repoRoot() {
  if (process.env.CLAUDE_PROJECT_DIR) return process.env.CLAUDE_PROJECT_DIR
  let d = dirname(fileURLToPath(import.meta.url))
  for (let i = 0; i < 6; i++) {
    if (existsSync(join(d, '.claude', 'settings.json'))) return d
    d = dirname(d)
  }
  return process.cwd()
}

/**
 * `--install` mode: does everything the deny message asks for, so the dev only
 * ever copy-pastes ONE command — adds the marketplaces from this repo's
 * settings.json, then installs each missing plugin project-scoped, running the
 * Claude CLI from the repo root regardless of where the dev invoked us.
 */
function runInstaller() {
  const dir = repoRoot()
  const bin = process.env.CLAUDE_BIN || 'claude'
  const settings = readJson(join(dir, '.claude', 'settings.json')) ?? {}
  const enabled = settings.enabledPlugins ?? {}
  const required = Object.keys(enabled).filter((k) => enabled[k] === true)
  if (required.length === 0) {
    console.log('No plugins declared in .claude/settings.json — nothing to do.')
    return
  }
  const reenabled = clearDisableOverrides(required, dir)

  const missing = required.filter((k) => installEntries(k, dir).length === 0)
  if (missing.length === 0) {
    if (reenabled > 0) {
      console.log('\nDone. Start a NEW Claude Code session (reopen the Claude panel) — the plugins load at session start.')
    } else {
      console.log(
        `Already installed and enabled for this repo: ${required.join(', ')}.\n` +
          'If Claude still blocks edits, the session predates the install — start a NEW Claude Code session.'
      )
    }
    return
  }

  addMarketplaces(settings, dir, bin)

  let failed = false
  for (const key of missing) {
    try {
      execFileSync(bin, ['plugin', 'install', '--scope', 'project', key], {
        cwd: dir,
        stdio: 'pipe',
      })
      console.log(`✓ installed: ${key}`)
    } catch (e) {
      failed = true
      console.error(`✗ failed to install ${key}: ${firstLine(e)}`)
    }
  }
  if (failed) {
    console.error(
      'Some installs failed. Check the error above — common causes: no access to the marketplace repo (needs GitHub auth) or no network.'
    )
    process.exit(1)
  }
  console.log('\nDone. Start a NEW Claude Code session (reopen the Claude panel) — the plugins load at session start.')
}

/** `claude plugin marketplace add` for every marketplace the repo's settings declare. */
function addMarketplaces(settings, dir, bin) {
  const marketplaces = settings.extraKnownMarketplaces ?? {}
  for (const [name, m] of Object.entries(marketplaces)) {
    const ref = m?.source?.repo || m?.source?.url || m?.source?.path
    if (!ref) continue
    try {
      execFileSync(bin, ['plugin', 'marketplace', 'add', ref], { cwd: dir, stdio: 'pipe' })
      console.log(`✓ marketplace added: ${name} (${ref})`)
    } catch (e) {
      if (e?.code === 'ENOENT') {
        console.error(
          `✗ Claude Code CLI ("${bin}") not found on PATH. Open a terminal where \`claude\` works and rerun this command.`
        )
        process.exit(1)
      }
      // Most likely already added — not fatal; the install step below is the real test.
      console.log(`• marketplace ${name}: already added (or: ${firstLine(e)})`)
    }
  }
}

/**
 * Remove `false` overrides for required plugins from .claude/settings.local.json —
 * a plugin disabled there stays unloaded no matter what is installed.
 * Returns the number of overrides removed.
 */
function clearDisableOverrides(required, dir) {
  const localPath = join(dir, '.claude', 'settings.local.json')
  const local = readJson(localPath)
  const disabled = required.filter((k) => local?.enabledPlugins?.[k] === false)
  if (disabled.length === 0) return 0
  for (const k of disabled) delete local.enabledPlugins[k]
  if (Object.keys(local.enabledPlugins).length === 0) delete local.enabledPlugins
  writeFileSync(localPath, JSON.stringify(local, null, 2) + '\n')
  console.log(`✓ re-enabled (removed disable override in .claude/settings.local.json): ${disabled.join(', ')}`)
  return disabled.length
}

function firstLine(e) {
  return String(e?.stderr || e?.message || e)
    .trim()
    .split('\n')[0]
}

function deny(reason) {
  process.stdout.write(
    JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason,
      },
    })
  )
  process.exit(0)
}

if (process.argv.includes('--install')) {
  runInstaller()
  process.exit(0)
}

try {
  const raw = readFileSync(0, 'utf8')
  if (!raw) process.exit(0)
  const event = JSON.parse(raw)
  if (event?.tool_name !== 'Edit' && event?.tool_name !== 'Write') process.exit(0)

  const file = String(event?.tool_input?.file_path ?? '')
  if (!file || !CODE_FILE.test(file)) process.exit(0)

  const dir = projectDir()
  const prefix = frontendPrefix(dir)
  if (prefix) {
    const inFrontend = file.startsWith(join(dir, prefix)) || file.startsWith(prefix)
    if (!inFrontend) process.exit(0)
  }

  const startMs = sessionStartMs(event)
  const missing = []
  const notLoaded = []
  const disabled = []
  for (const key of requiredPlugins(dir)) {
    if (locallyDisabled(key, dir)) {
      disabled.push(key)
      continue
    }
    const entries = installEntries(key, dir)
    if (entries.length === 0) missing.push(key)
    else if (installedMidSession(entries, startMs)) notLoaded.push(key)
  }

  if (disabled.length > 0) {
    deny(
      `This repo requires the ${disabled.join(', ')} plugin(s), but they are DISABLED for this checkout ` +
        `(an enabledPlugins override in .claude/settings.local.json), so the team's skills and guard hooks ` +
        `are not active in this session. Code edits are blocked until re-enabled. ` +
        `Tell the developer: open a terminal at the repo root and copy-paste exactly this ONE command ` +
        `(not a /slash command — it works in any terminal, including VS Code's): ` +
        `node .claude/hooks/require-plugin.mjs --install ` +
        `— it removes the disable override (and installs anything missing). When it prints "Done", ` +
        `start a NEW Claude Code session and retry there. Do not write or edit code until then.`
    )
  }

  if (missing.length > 0) {
    deny(
      `This repo requires the ${missing.join(', ')} plugin(s), which are not installed for this project — ` +
        `so the team's skills and guard hooks are not active in this session. Code edits are blocked until installed. ` +
        `Tell the developer: open a terminal at the repo root and copy-paste exactly this ONE command ` +
        `(not a /slash command — it works in any terminal, including VS Code's): ` +
        `node .claude/hooks/require-plugin.mjs --install ` +
        `— it sets up everything (marketplace + plugins). When it prints "Done", start a NEW Claude Code session ` +
        `and retry there. Do not write or edit code until then.`
    )
  }

  if (notLoaded.length > 0) {
    deny(
      `The ${notLoaded.join(', ')} plugin(s) are installed, but the install happened after this ` +
        `session started, so their skills and guard hooks are not active yet. Nothing more to ` +
        `install — the developer just needs to start a NEW Claude Code session (reopen the Claude ` +
        `panel, or rerun \`claude\` in the terminal) and retry there. Do not write or edit code until then.`
    )
  }

  process.exit(0)
} catch {
  // Never block an action because of a hook error.
  process.exit(0)
}
