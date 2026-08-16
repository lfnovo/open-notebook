# Communication Templates

Reference implementation: the v1.11.0 release
(https://github.com/lfnovo/open-notebook/releases/tag/v1.11.0).

## GitHub release notes structure

```
**We recommend all users upgrade.** <one-line verdict: what this release is,
and that it was validated by the release test process>

## 🔒 Security hardening        (if applicable — lead with it)
## ✨ New features               (user language, issue refs)
## ⚡ Performance
## 🐛 Notable fixes
## ⚠️ Behavior changes for self-hosters
    <anything that can require a config tweak on upgrade — numbered,
     each with the escape hatch (env var, override file, doc link)>
## 🙏 Thanks                     (MANDATORY — see below)
Full details in the [CHANGELOG](.../CHANGELOG.md).
```

Tone: honest and specific. Say what protections do AND what stays supported
(e.g. "private IPs/localhost remain fully supported for self-hosted Ollama").

## 🙏 Thanks — collecting contributors (never skip, never miss anyone)

1. Commit authors in the release range:
   `git log <last-tag>..<tag> --pretty='%an <%ae>' | sort | uniq -c | sort -rn`
2. Map every non-obvious name to a GitHub handle via their PR:
   `gh pr view <n> --json author --jq .author.login`
   (PR list: `gh pr list --state merged --limit 100 --json number,author,mergedAt,title`
   filtered to merges after the previous tag — beware PRs merged before the
   previous tag was cut appearing in date filters.)
3. One bullet per contributor: **@handle** — what they shipped, with refs.
4. Close with a collective thank-you to issue reporters.
5. Bots (dependabot) are excluded.

## Discord announcement skeleton

```
📢 Open Notebook v<X.Y.Z> is out — <hook: why upgrade>!

<2-3 lines: the headline theme (e.g. security pass) + feature highlights
as a one-line · separated list>

⚡ <performance line, if any>

🧪 <one line on how it was tested — users trust releases more when they
    know fresh-install + upgrade were tested on the real images>

⚠️ Self-hosters: check "Behavior changes" in the release notes.

📝 https://github.com/lfnovo/open-notebook/releases/tag/v<X.Y.Z>
🐳 docker pull lfnovo/open_notebook:v1-latest
```

Consider crediting contributors on Discord too — communities love it.

The owner posts to Discord; deliver final text, don't post.
