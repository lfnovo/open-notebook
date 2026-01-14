# Prior Notebook - Nomad Job Specification
# Military-grade RAG for quantitative trading

job "prior-notebook" {
  datacenters = ["dc1"]
  type        = "service"

  # Update strategy
  update {
    max_parallel     = 1
    min_healthy_time = "30s"
    healthy_deadline = "5m"
    auto_revert      = true
    canary           = 1
  }

  # Reschedule on failure
  reschedule {
    delay          = "30s"
    delay_function = "exponential"
    max_delay      = "1h"
    unlimited      = true
  }

  group "prior-api" {
    count = 2

    # Spread across different nodes
    spread {
      attribute = "${node.unique.id}"
    }

    network {
      port "http" {
        to = 8080
      }
    }

    service {
      name = "prior-api"
      port = "http"

      tags = [
        "traefik.enable=true",
        "traefik.http.routers.prior.rule=Host(`notebook.prior-systems.com`)",
        "traefik.http.routers.prior.tls=true",
        "traefik.http.routers.prior.tls.certresolver=letsencrypt",
      ]

      check {
        type     = "http"
        path     = "/health"
        interval = "10s"
        timeout  = "3s"
      }
    }

    task "api" {
      driver = "docker"

      config {
        image = "ghcr.io/prior-systems/prior-notebook:latest"
        ports = ["http"]

        volumes = [
          "local/config.toml:/app/config.toml:ro",
        ]
      }

      template {
        data = <<EOF
[server]
host = "0.0.0.0"
port = 8080
workers = {{ env "NOMAD_CPU_LIMIT" | parseInt | divide 250 }}

[database]
questdb_host = "{{ range service "questdb" }}{{ .Address }}{{ end }}"
questdb_port = {{ range service "questdb" }}{{ .Port }}{{ end }}
redis_url = "redis://{{ range service "redis" }}{{ .Address }}:{{ .Port }}{{ end }}"
qdrant_url = "http://{{ range service "qdrant" }}{{ .Address }}:{{ .Port }}{{ end }}"
qdrant_collection = "prior_notebook"

[security]
jwt_secret = "{{ with secret "secret/data/prior-notebook" }}{{ .Data.data.jwt_secret }}{{ end }}"
jwt_expiry_hours = 24
allowed_wireguard_ips = ["10.0.0.0/8"]
enable_zero_trust = true

[search]
arxiv_max_results = 50
embedding_model = "BAAI/bge-small-en-v1.5"
embedding_dimension = 384

[llm]
default_provider = "anthropic"
anthropic_api_key = "{{ with secret "secret/data/prior-notebook" }}{{ .Data.data.anthropic_key }}{{ end }}"
default_model = "claude-sonnet-4-20250514"
max_tokens = 4096
temperature = 0.7
EOF
        destination = "local/config.toml"
      }

      env {
        RUST_LOG = "info"
      }

      resources {
        cpu    = 1000
        memory = 512
      }
    }
  }

  # Qdrant Vector Database
  group "qdrant" {
    count = 1

    network {
      port "http" {
        to = 6333
      }
      port "grpc" {
        to = 6334
      }
    }

    service {
      name = "qdrant"
      port = "grpc"

      check {
        type     = "http"
        path     = "/readyz"
        port     = "http"
        interval = "10s"
        timeout  = "3s"
      }
    }

    task "qdrant" {
      driver = "docker"

      config {
        image = "qdrant/qdrant:v1.12.0"
        ports = ["http", "grpc"]

        volumes = [
          "qdrant-data:/qdrant/storage",
        ]
      }

      resources {
        cpu    = 500
        memory = 1024
      }
    }
  }

  # Redis Cache
  group "redis" {
    count = 1

    network {
      port "redis" {
        to = 6379
      }
    }

    service {
      name = "redis"
      port = "redis"

      check {
        type     = "tcp"
        interval = "10s"
        timeout  = "2s"
      }
    }

    task "redis" {
      driver = "docker"

      config {
        image = "redis:7-alpine"
        ports = ["redis"]
        args  = ["redis-server", "--maxmemory", "256mb", "--maxmemory-policy", "allkeys-lru"]
      }

      resources {
        cpu    = 200
        memory = 256
      }
    }
  }
}
