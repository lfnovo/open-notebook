{{- /*
Copyright © 2024 Luis Novo

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/ -}}

{{- /*
Default labels for Open Notebook resources
*/ -}}
{{- define "open-notebook.labels" -}}
{{- include "common.labels.standard" . | nindent 0 }}
{{- end }}

{{- /*
Selector labels for Open Notebook resources
*/ -}}
{{- define "open-notebook.selectorLabels" -}}
{{- include "common.labels.matchLabels" . | nindent 0 }}
{{ end }}

{{- /*
SurrealDB labels
*/ -}}
{{- define "open-notebook.surrealdb.labels" -}}
helm.sh/chart: {{ include "common.names.chart" . }}
{{ include "open-notebook.surrealdb.selectorLabels" . }}
{{- if .Chart.AppVersion -}}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{- /*
SurrealDB selector labels
*/ -}}
{{- define "open-notebook.surrealdb.selectorLabels" -}}
app.kubernetes.io/name: {{ include "common.names.name" . }}-surrealdb
app.kubernetes.io/instance: {{ .Release.Name }}
{{ end }}

{{- /*
Return the secret name for SurrealDB
*/ -}}
{{- define "open-notebook.surrealdb.secretName" -}}
{{- if .Values.surrealdb.auth.existingSecret -}}
{{- .Values.surrealdb.auth.existingSecret -}}
{{- else -}}
{{- printf "%s-surrealdb" (include "common.names.fullname" .) -}}
{{- end -}}
{{- end -}}

{{- /*
Return the secret name for application
*/ -}}
{{- define "open-notebook.secretName" -}}
{{- if .Values.config.auth.existingSecret -}}
{{- .Values.config.auth.existingSecret -}}
{{- else -}}
{{- include "common.names.fullname" . -}}
{{- end -}}
{{- end -}}

{{- /*
Get the image registry
*/ -}}
{{- define "open-notebook.imageRegistry" -}}
{{- if .Values.global.imageRegistry -}}
{{- .Values.global.imageRegistry -}}
{{- else if .Values.image.registry -}}
{{- .Values.image.registry -}}
{{- end }}
{{- end }}

{{- /*
Get the application image
*/ -}}
{{- define "open-notebook.image" -}}
{{- $registry := include "open-notebook.imageRegistry" . -}}
{{- $tag := default .Chart.AppVersion .Values.image.tag | default "v1-latest" -}}
{{- if .Values.image.useGHCR -}}
{{- $ghcrTag := default .Chart.AppVersion .Values.image.ghcr.tag | default "v1-latest" -}}
{{- printf "%s/%s:%s" .Values.image.ghcr.registry .Values.image.ghcr.repository $ghcrTag -}}
{{- else -}}
{{- printf "%s/%s:%s" $registry .Values.image.repository $tag -}}
{{- end }}
{{- end }}

{{- /*
Get the SurrealDB image
*/ -}}
{{- define "open-notebook.surrealdb.image" -}}
{{- $registry := .Values.surrealdb.image.registry -}}
{{- $tag := default "v2" .Values.surrealdb.image.tag -}}
{{- printf "%s/%s:%s" $registry .Values.surrealdb.image.repository $tag -}}
{{- end }}

{{- /*
Get the SurrealDB URL
*/ -}}
{{- define "open-notebook.surrealdb.url" -}}
{{- if .Values.surrealdb.external.enabled -}}
{{- if .Values.surrealdb.external.secure -}}
wss://{{ .Values.surrealdb.external.host }}:{{ .Values.surrealdb.external.port }}/rpc
{{- else -}}
ws://{{ .Values.surrealdb.external.host }}:{{ .Values.surrealdb.external.port }}/rpc
{{- end }}
{{- else -}}
ws://{{ include "common.names.fullname" . }}-surrealdb.{{ .Release.Namespace }}.svc.{{ .Values.global.clusterDomain }}:8000/rpc
{{- end }}
{{- end }}

{{- /*
Get the API URL for browser access
*/ -}}
{{- define "open-notebook.api.url" -}}
{{- if .Values.config.api.url -}}
{{- .Values.config.api.url -}}
{{- else if .Values.ingress.enabled -}}
{{- if .Values.ingress.tls }}
https://{{ (index .Values.ingress.hosts 0).host }}
{{- else -}}
http://{{ (index .Values.ingress.hosts 0).host }}
{{- end }}
{{- else if eq .Values.service.type "LoadBalancer" -}}
http://localhost:{{ .Values.app.ports.api }}
{{- else -}}
http://localhost:{{ .Values.app.ports.api }}
{{- end }}
{{- end }}

{{- /*
Get the internal API URL
*/ -}}
{{- define "open-notebook.api.internalUrl" -}}
{{- if .Values.config.api.internalUrl -}}
{{- .Values.config.api.internalUrl -}}
{{- else -}}
http://localhost:{{ .Values.app.ports.api }}
{{- end }}
{{- end }}

{{- /*
Render environment variables for the application
*/ -}}
{{- define "open-notebook.envVars" -}}
- name: API_URL
  value: {{ include "open-notebook.api.url" . | quote }}
- name: INTERNAL_API_URL
  value: {{ include "open-notebook.api.internalUrl" . | quote }}
- name: API_CLIENT_TIMEOUT
  value: {{ .Values.config.api.clientTimeout | quote }}
- name: ESPERANTO_LLM_TIMEOUT
  value: {{ .Values.config.api.esperantoTimeout | quote }}
- name: SURREAL_URL
  value: {{ include "open-notebook.surrealdb.url" . | quote }}
- name: SURREAL_USER
  value: {{ .Values.surrealdb.auth.user | quote }}
{{ if or .Values.surrealdb.auth.password .Values.surrealdb.auth.existingSecret -}}
- name: SURREAL_PASSWORD
  valueFrom:
    secretKeyRef:
      name: {{ include "open-notebook.surrealdb.secretName" . }}
      key: {{ .Values.surrealdb.auth.secretKey.password | default "password" }}
{{- end }}
- name: SURREAL_NAMESPACE
  value: {{ .Values.surrealdb.database.namespace | quote }}
- name: SURREAL_DATABASE
  value: {{ .Values.surrealdb.database.database | quote }}
{{ if .Values.config.ssl.caBundle -}}
- name: ESPERANTO_SSL_CA_BUNDLE
  value: {{ .Values.config.ssl.caBundle | quote }}
{{- end }}
- name: ESPERANTO_SSL_VERIFY
  value: {{ .Values.config.ssl.verify | quote }}
- name: SURREAL_COMMANDS_MAX_TASKS
  value: {{ .Values.config.worker.maxTasks | quote }}
- name: SURREAL_COMMANDS_RETRY_ENABLED
  value: {{ .Values.config.worker.retry.enabled | quote }}
- name: SURREAL_COMMANDS_RETRY_MAX_ATTEMPTS
  value: {{ .Values.config.worker.retry.maxAttempts | quote }}
- name: SURREAL_COMMANDS_RETRY_WAIT_STRATEGY
  value: {{ .Values.config.worker.retry.waitStrategy | quote }}
- name: SURREAL_COMMANDS_RETRY_WAIT_MIN
  value: {{ .Values.config.worker.retry.waitMin | quote }}
- name: SURREAL_COMMANDS_RETRY_WAIT_MAX
  value: {{ .Values.config.worker.retry.waitMax | quote }}
- name: TTS_BATCH_SIZE
  value: {{ .Values.config.tts.batchSize | quote }}
{{ if or .Values.config.aiProviders.openai.apiKey .Values.config.aiProviders.openai.existingSecret -}}
{{ if .Values.config.aiProviders.openai.existingSecret -}}
- name: OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.openai.existingSecret }}
      key: {{ .Values.config.aiProviders.openai.secretKey }}
{{- else -}}
- name: OPENAI_API_KEY
  value: {{ .Values.config.aiProviders.openai.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.anthropic.apiKey .Values.config.aiProviders.anthropic.existingSecret -}}
{{ if .Values.config.aiProviders.anthropic.existingSecret -}}
- name: ANTHROPIC_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.anthropic.existingSecret }}
      key: {{ .Values.config.aiProviders.anthropic.secretKey }}
{{- else -}}
- name: ANTHROPIC_API_KEY
  value: {{ .Values.config.aiProviders.anthropic.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.google.apiKey .Values.config.aiProviders.google.existingSecret -}}
{{ if .Values.config.aiProviders.google.existingSecret -}}
- name: GOOGLE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.google.existingSecret }}
      key: {{ .Values.config.aiProviders.google.secretKey }}
{{- else -}}
- name: GOOGLE_API_KEY
  value: {{ .Values.config.aiProviders.google.apiKey | quote }}
{{- end }}
{{- end }}

{{ if .Values.config.aiProviders.google.geminiBaseUrl -}}
- name: GEMINI_API_BASE_URL
  value: {{ .Values.config.aiProviders.google.geminiBaseUrl | quote }}
{{- end }}

{{ if .Values.config.aiProviders.vertexai.project -}}
- name: VERTEX_PROJECT
  value: {{ .Values.config.aiProviders.vertexai.project | quote }}
{{- end }}

{{ if .Values.config.aiProviders.vertexai.credentials -}}
- name: GOOGLE_APPLICATION_CREDENTIALS
  value: {{ .Values.config.aiProviders.vertexai.credentials | quote }}
{{- end }}

{{ if .Values.config.aiProviders.vertexai.location -}}
- name: VERTEX_LOCATION
  value: {{ .Values.config.aiProviders.vertexai.location | quote }}
{{- end }}

{{- if or .Values.config.aiProviders.mistral.apiKey .Values.config.aiProviders.mistral.existingSecret -}}
{{ if .Values.config.aiProviders.mistral.existingSecret -}}
- name: MISTRAL_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.mistral.existingSecret }}
      key: {{ .Values.config.aiProviders.mistral.secretKey }}
{{- else -}}
- name: MISTRAL_API_KEY
  value: {{ .Values.config.aiProviders.mistral.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.deepseek.apiKey .Values.config.aiProviders.deepseek.existingSecret -}}
{{ if .Values.config.aiProviders.deepseek.existingSecret -}}
- name: DEEPSEEK_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.deepseek.existingSecret }}
      key: {{ .Values.config.aiProviders.deepseek.secretKey }}
{{- else -}}
- name: DEEPSEEK_API_KEY
  value: {{ .Values.config.aiProviders.deepseek.apiKey | quote }}
{{- end }}
{{- end }}

{{ if .Values.config.aiProviders.ollama.baseUrl -}}
- name: OLLAMA_API_BASE
  value: {{ .Values.config.aiProviders.ollama.baseUrl | quote }}
{{- end }}

{{ if .Values.config.aiProviders.openrouter.baseUrl -}}
- name: OPENROUTER_BASE_URL
  value: {{ .Values.config.aiProviders.openrouter.baseUrl | quote }}
{{- end }}

{{- if or .Values.config.aiProviders.openrouter.apiKey .Values.config.aiProviders.openrouter.existingSecret -}}
{{ if .Values.config.aiProviders.openrouter.existingSecret -}}
- name: OPENROUTER_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.openrouter.existingSecret }}
      key: {{ .Values.config.aiProviders.openrouter.secretKey }}
{{- else -}}
- name: OPENROUTER_API_KEY
  value: {{ .Values.config.aiProviders.openrouter.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.groq.apiKey .Values.config.aiProviders.groq.existingSecret -}}
{{ if .Values.config.aiProviders.groq.existingSecret -}}
- name: GROQ_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.groq.existingSecret }}
      key: {{ .Values.config.aiProviders.groq.secretKey }}
{{- else -}}
- name: GROQ_API_KEY
  value: {{ .Values.config.aiProviders.groq.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.xai.apiKey .Values.config.aiProviders.xai.existingSecret -}}
{{ if .Values.config.aiProviders.xai.existingSecret -}}
- name: XAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.xai.existingSecret }}
      key: {{ .Values.config.aiProviders.xai.secretKey }}
{{- else -}}
- name: XAI_API_KEY
  value: {{ .Values.config.aiProviders.xai.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.elevenlabs.apiKey .Values.config.aiProviders.elevenlabs.existingSecret -}}
{{ if .Values.config.aiProviders.elevenlabs.existingSecret -}}
- name: ELEVENLABS_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.elevenlabs.existingSecret }}
      key: {{ .Values.config.aiProviders.elevenlabs.secretKey }}
{{- else -}}
- name: ELEVENLABS_API_KEY
  value: {{ .Values.config.aiProviders.elevenlabs.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.voyage.apiKey .Values.config.aiProviders.voyage.existingSecret -}}
{{ if .Values.config.aiProviders.voyage.existingSecret -}}
- name: VOYAGE_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.voyage.existingSecret }}
      key: {{ .Values.config.aiProviders.voyage.secretKey }}
{{- else -}}
- name: VOYAGE_API_KEY
  value: {{ .Values.config.aiProviders.voyage.apiKey | quote }}
{{- end }}
{{- end }}

{{ if .Values.config.aiProviders.openaiCompatible.baseUrl -}}
- name: OPENAI_COMPATIBLE_BASE_URL
  value: {{ .Values.config.aiProviders.openaiCompatible.baseUrl | quote }}
{{- end }}

{{- if or .Values.config.aiProviders.azureOpenai.apiKey .Values.config.aiProviders.azureOpenai.existingSecret -}}
{{ if .Values.config.aiProviders.azureOpenai.existingSecret -}}
- name: AZURE_OPENAI_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.azureOpenai.existingSecret }}
      key: {{ .Values.config.aiProviders.azureOpenai.secretKey | default "azure-openai-api-key" }}
{{- else -}}
- name: AZURE_OPENAI_API_KEY
  value: {{ .Values.config.aiProviders.azureOpenai.apiKey | quote }}
{{- end }}
{{- end }}

{{ if .Values.config.aiProviders.azureOpenai.endpoint -}}
- name: AZURE_OPENAI_ENDPOINT
  value: {{ .Values.config.aiProviders.azureOpenai.endpoint | quote }}
{{- end }}

{{ if .Values.config.aiProviders.azureOpenai.apiVersion -}}
- name: AZURE_OPENAI_API_VERSION
  value: {{ .Values.config.aiProviders.azureOpenai.apiVersion | quote }}
{{- end }}

{{ if .Values.config.aiProviders.langchain.tracingV2 -}}
- name: LANGCHAIN_TRACING_V2
  value: {{ .Values.config.aiProviders.langchain.tracingV2 | quote }}
{{- end }}

{{ if .Values.config.aiProviders.langchain.endpoint -}}
- name: LANGCHAIN_ENDPOINT
  value: {{ .Values.config.aiProviders.langchain.endpoint | quote }}
{{- end }}

{{- if or .Values.config.aiProviders.langchain.apiKey .Values.config.aiProviders.langchain.existingSecret -}}
{{ if .Values.config.aiProviders.langchain.existingSecret -}}
- name: LANGCHAIN_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.langchain.existingSecret }}
      key: {{ .Values.config.aiProviders.langchain.secretKey }}
{{- else -}}
- name: LANGCHAIN_API_KEY
  value: {{ .Values.config.aiProviders.langchain.apiKey | quote }}
{{- end }}
{{- end }}

{{ if .Values.config.aiProviders.langchain.project -}}
- name: LANGCHAIN_PROJECT
  value: {{ .Values.config.aiProviders.langchain.project | quote }}
{{- end }}

{{- if or .Values.config.aiProviders.firecrawl.apiKey .Values.config.aiProviders.firecrawl.existingSecret -}}
{{ if .Values.config.aiProviders.firecrawl.existingSecret -}}
- name: FIRECRAWL_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.firecrawl.existingSecret }}
      key: {{ .Values.config.aiProviders.firecrawl.secretKey }}
{{- else -}}
- name: FIRECRAWL_API_KEY
  value: {{ .Values.config.aiProviders.firecrawl.apiKey | quote }}
{{- end }}
{{- end }}

{{- if or .Values.config.aiProviders.jina.apiKey .Values.config.aiProviders.jina.existingSecret -}}
{{ if .Values.config.aiProviders.jina.existingSecret -}}
- name: JINA_API_KEY
  valueFrom:
    secretKeyRef:
      name: {{ .Values.config.aiProviders.jina.existingSecret }}
      key: {{ .Values.config.aiProviders.jina.secretKey }}
{{- else -}}
- name: JINA_API_KEY
  value: {{ .Values.config.aiProviders.jina.apiKey | quote }}
{{- end }}
{{- end }}
{{- end }}
