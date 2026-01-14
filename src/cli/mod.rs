//! Dynamic CLI for Prior Notebook

pub mod commands;

use clap::{Parser, Subcommand};

/// Prior Notebook - Military-grade RAG for quantitative trading
#[derive(Parser)]
#[command(name = "prior")]
#[command(author = "Prior Systems")]
#[command(version)]
#[command(about = "RAG system for quantitative trading research", long_about = None)]
pub struct Cli {
    #[command(subcommand)]
    pub command: Commands,

    /// Configuration file path
    #[arg(short, long, global = true, default_value = "config.toml")]
    pub config: String,

    /// Enable verbose output
    #[arg(short, long, global = true)]
    pub verbose: bool,
}

#[derive(Subcommand)]
pub enum Commands {
    /// Search the knowledge base
    Search {
        /// Search query
        query: String,

        /// Maximum results to return
        #[arg(short, long, default_value = "10")]
        limit: usize,

        /// Output format (json, table, markdown)
        #[arg(short, long, default_value = "table")]
        format: String,
    },

    /// Search arXiv for papers
    Arxiv {
        /// Search query
        query: String,

        /// Maximum results
        #[arg(short, long, default_value = "20")]
        max_results: usize,

        /// Ingest results into knowledge base
        #[arg(short, long)]
        ingest: bool,
    },

    /// Ingest documents
    Ingest {
        #[command(subcommand)]
        source: IngestSource,
    },

    /// Query trading data
    Trading {
        #[command(subcommand)]
        data: TradingData,
    },

    /// Start the API server
    Serve {
        /// Host to bind to
        #[arg(short = 'H', long, default_value = "127.0.0.1")]
        host: String,

        /// Port to listen on
        #[arg(short, long, default_value = "8080")]
        port: u16,

        /// Number of workers
        #[arg(short, long)]
        workers: Option<usize>,
    },

    /// Manage security settings
    Security {
        #[command(subcommand)]
        action: SecurityAction,
    },
}

#[derive(Subcommand)]
pub enum IngestSource {
    /// Ingest a PDF file
    Pdf {
        /// Path to PDF file or directory
        path: String,

        /// Recursively process directories
        #[arg(short, long)]
        recursive: bool,
    },

    /// Ingest from URL
    Url {
        /// URL to fetch and ingest
        url: String,
    },

    /// Ingest plain text
    Text {
        /// Title for the document
        title: String,

        /// File containing text (or - for stdin)
        #[arg(short, long)]
        file: Option<String>,
    },
}

#[derive(Subcommand)]
pub enum TradingData {
    /// Get GEX (Gamma Exposure) data
    Gex {
        /// Symbol (e.g., SPY, QQQ)
        symbol: String,

        /// Number of days to fetch
        #[arg(short, long, default_value = "7")]
        days: i32,

        /// Output format
        #[arg(short, long, default_value = "table")]
        format: String,
    },

    /// Get Vanna data
    Vanna {
        /// Symbol
        symbol: String,

        /// Number of days
        #[arg(short, long, default_value = "7")]
        days: i32,
    },

    /// Run custom SQL query on QuestDB
    Query {
        /// SQL query
        sql: String,
    },
}

#[derive(Subcommand)]
pub enum SecurityAction {
    /// Generate a new JWT secret
    GenerateSecret,

    /// Test Zero Trust configuration
    TestZeroTrust {
        /// IP to test
        ip: String,
    },

    /// Hash a password
    HashPassword {
        /// Password to hash
        password: String,
    },
}
