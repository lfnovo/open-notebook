# AI provider terms

Every AI provider this product can call, with a pointer to its commercial
terms, and the ones that need legal review before we enable them commercially.

> **Not legal advice, and not a clearance.** This is an engineering inventory
> to hand to counsel. Provider terms change without notice — every link must be
> re-checked at review time, and again before launch.

## Why this file exists

The MIT licence gives us the *code*. It says nothing about the *services* the
code calls. When our product sends a customer's research to OpenAI, Anthropic
or anyone else, **that provider's commercial terms govern the call** — and some
of them restrict exactly what we intend to do: offer a paid product built on
top of their API.

The provider list is generated from the real registry
(`open_notebook/ai/provider_registry.py` → `PROVIDERS`), so it is the actual
set the application can reach, not an assumed one. **22 providers**, more than
the 8 named in the original plan.

## The three questions counsel needs to answer per provider

1. **Resale / downstream use** — may we build a paid commercial product on this
   API and serve it to our own customers?
2. **Data handling** — is customer content used to train the provider's models?
   Is there a business/enterprise tier that contractually excludes that? What
   is the retention period?
3. **Jurisdiction & residency** — where is the data processed, and does that
   satisfy our clients' compliance requirements?

## Provider inventory

Legend — **LLM**: chat/completions · **embed**: embeddings · **STT**:
speech-to-text · **TTS**: text-to-speech.

| Provider | Modalities | Console / docs | Commercial terms | Flag |
|---|---|---|---|---|
| OpenAI | LLM, embed, STT, TTS | [keys](https://platform.openai.com/api-keys) | <https://openai.com/policies/business-terms> | ⚠️ Confirm API data is excluded from training by default |
| Anthropic | LLM | [console](https://console.anthropic.com/settings/keys) | <https://www.anthropic.com/legal/commercial-terms> | ⚠️ Review commercial terms |
| Google AI (Gemini) | LLM, embed, STT, TTS | [AI Studio](https://aistudio.google.com/app/apikey) | <https://ai.google.dev/gemini-api/terms> | 🚩 **Free tier may permit training on inputs** — paid tier required |
| Google Vertex AI | LLM, embed, TTS | [docs](https://cloud.google.com/vertex-ai/docs/start/cloud-environment) | <https://cloud.google.com/terms/service-terms> | ⚠️ Governed by GCP terms; generally enterprise-safe |
| Azure OpenAI | LLM, embed, STT, TTS | [portal](https://portal.azure.com/) | <https://azure.microsoft.com/support/legal/> | ⚠️ Usually the strongest enterprise posture |
| Groq | LLM, STT | [console](https://console.groq.com/keys) | <https://groq.com/terms-of-sale/> | ⚠️ Review |
| Mistral AI | LLM, embed, STT, TTS | [console](https://console.mistral.ai/api-keys/) | <https://mistral.ai/terms/> | ⚠️ Review |
| DeepSeek | LLM | [platform](https://platform.deepseek.com/api_keys) | <https://platform.deepseek.com/downloads/DeepSeek%20Open%20Platform%20Terms%20of%20Service.html> | 🚩 **PRC jurisdiction** — data residency |
| xAI (Grok) | LLM, TTS | [console](https://console.x.ai/) | <https://x.ai/legal/terms-of-service> | ⚠️ Review |
| OpenRouter | LLM, embed, STT, TTS | [keys](https://openrouter.ai/keys) | <https://openrouter.ai/terms> | 🚩 **Aggregator** — upstream model terms also apply |
| DashScope (Qwen) | LLM | [docs](https://help.aliyun.com/zh/model-studio/getting-started/) | <https://www.alibabacloud.com/help/en/legal> | 🚩 **PRC jurisdiction** (Alibaba) — data residency |
| MiniMax | LLM | [docs](https://platform.minimaxi.com/document/Guides) | <https://www.minimaxi.com/protocol/terms-of-service> | 🚩 **PRC jurisdiction** — data residency |
| Novita | LLM | [keys](https://novita.ai/settings/key-management) | <https://novita.ai/legal/terms-of-service> | 🚩 Smaller vendor — verify resale terms |
| PayPerQ (ppq) | LLM, embed, STT, TTS | [site](https://ppq.ai) | <https://ppq.ai> | 🚩 **Small vendor, terms unclear** — verify before enabling |
| Cohere | LLM, embed | [dashboard](https://dashboard.cohere.com/api-keys) | <https://cohere.com/terms-of-use> | ⚠️ Trial keys are explicitly non-commercial — production key required |
| Voyage AI | embed | [dashboard](https://dash.voyageai.com/api-keys) | <https://www.voyageai.com/terms-of-service> | ⚠️ Review |
| ElevenLabs | TTS, STT | [settings](https://elevenlabs.io/app/settings/api-keys) | <https://elevenlabs.io/terms-of-use> | 🚩 **Voice cloning + commercial audio rights** — see below |
| Deepgram | TTS, STT | [console](https://console.deepgram.com/) | <https://deepgram.com/terms> | ⚠️ Review |
| Ollama | LLM, embed | local | n/a — no service terms | 🚩 **Model weight licences apply instead** — see below |
| oMLX | LLM, embed | local | n/a — no service terms | 🚩 **Model weight licences apply instead** — see below |
| OpenAI Compatible | LLM, embed, STT, TTS | user-configured endpoint | **depends on operator** | 🚩 Cannot be assessed centrally — see below |
| Anthropic Compatible | LLM | user-configured endpoint | **depends on operator** | 🚩 Cannot be assessed centrally — see below |

## Flagged issues, explained

### 🚩 Local inference shifts the question to model licences (Ollama, oMLX)

There is no service ToS for locally-run models — but that does **not** mean
there is no licence question. It moves to the **model weights**, and some are
genuinely restrictive for commercial use:

- **Llama** models carry Meta's community licence, which imposes conditions
  above a monthly-active-user threshold and adds naming/attribution
  requirements.
- **Gemma** carries Google's use policy.
- Others are Apache-2.0 or MIT and unproblematic.

**Action:** if we ship or recommend specific local models, each model's licence
needs its own review. Letting a *customer* choose an arbitrary model shifts that
obligation to them — which should be stated in our terms of service.

### 🚩 "Compatible" endpoints cannot be assessed centrally

`OpenAI Compatible` and `Anthropic Compatible` point at whatever URL the
operator configures — vLLM, LM Studio, llama.cpp, or a third-party reseller.
The governing terms are whoever runs that endpoint's.

**Action:** our terms of service should place responsibility for
customer-configured endpoints on the customer. No central clearance is possible.

### 🚩 PRC-jurisdiction providers (DeepSeek, DashScope/Qwen, MiniMax)

These process data under PRC law. For enterprise clients — especially in
regulated sectors, government, or the EU — this is frequently a contractual
blocker regardless of the provider's own terms.

**Action:** decide whether these ship **enabled by default**. The safer default
is to make them opt-in per deployment, with the residency implication surfaced
in the UI. This is a product decision as much as a legal one.

### 🚩 Aggregators (OpenRouter)

OpenRouter proxies many upstream models. Its terms govern the proxy; the
underlying model provider's terms still reach the actual inference. Effectively
two licence layers, and the second is not visible to us.

### 🚩 ElevenLabs — commercial audio rights

The podcast feature generates distributable audio. Rights to *commercially use
generated speech* — and any voice-cloning restrictions — vary by plan tier.
Since our product's output is intended for our customers' use, this needs
explicit confirmation that the tier we ship permits commercial distribution of
generated audio.

### ⚠️ Cohere trial keys

Cohere distinguishes trial from production keys, and trial keys are explicitly
not for commercial use. Ensure any bundled or documented credential is a
production key.

## What must happen before commercial launch

1. **Decide the enabled-by-default set.** Every provider in the registry is
   reachable, but we need not enable all 22. Recommendation: default to
   providers with clear enterprise terms (OpenAI, Anthropic, Azure, Vertex,
   Bedrock-class), and make the rest opt-in per deployment.
2. **Get counsel sign-off** on the default set against the three questions
   above.
3. **Confirm no-training guarantees** in writing for every default provider —
   customer research content is the product's core asset.
4. **Write the customer-facing position**: which providers we call, what data
   leaves the deployment, and where it is processed. Clients will ask, and
   under GDPR-style regimes they are entitled to know.
5. **Assign responsibility for customer-configured endpoints and local models**
   in our terms of service.
6. **Re-verify every link in this table.** They are starting points captured
   during WP1, not verified clearances.

## Keeping this file accurate

The provider list is derived from `open_notebook/ai/provider_registry.py`. When
a provider is added there, **add it here too** — a provider the product can call
but that legal has never reviewed is exactly the gap this file exists to close.

Regenerate the current list with:

```bash
uv run python -c "
from open_notebook.ai.provider_registry import PROVIDERS
for k, v in PROVIDERS.items():
    print(f'{k:22} {v.display_name:24} {\",\".join(v.modalities)}')
"
```
