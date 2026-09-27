# Account model selection

Preliminary research and preliminary merge discover available models before inference:
Codex app-server model/list + account/rateLimits/read, Claude stream-JSON initialize,
and Gemini CLI models. Discovery submits no research prompt. Authentication remains
in the installed CLI; no API key or cookie transfer is introduced.

The explicit quality policy ranks Astra/Fable first, then their model families;
Gemini Pro precedes Flash. Versions rank within a family. The policy selects the
maximum reasoning effort supported by the account catalog, not an invented flag.
Catalogs are cached for 60 seconds per provider. Unknown new model families require
a ranking-policy update: these are maintained preferences, not universal quality
scores.

A model-not-found response before output/tools can select the next ranked candidate
(maximum three attempts, identical evidence). Selected model, effort, skipped models
and provider-reported identity are retained in execution metadata. Partial output,
authentication, quota and timeout errors do not trigger that fallback. Account-wide
quota blocks replacement calls; a persisted 60-second cooldown avoids immediate
repetition. Codex exposes quota before sending; Claude/Gemini do not expose comparable
remaining-credit data through these interfaces, so availability remains unknown
until provider feedback. No usage-reset credits are consumed.

Large-packet synthesis retains its measured model/effort fingerprint. Changing it
requires fresh context calibration; shared evidence is never shortened to fit an
alternative. Web Deep Research has a separate quota and never silently becomes
ordinary account research. Missing mode and positively identified quota exhaustion
remain different states.
