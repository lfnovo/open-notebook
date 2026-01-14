//! CLI command implementations

use anyhow::Result;
use console::{style, Term};
use indicatif::{ProgressBar, ProgressStyle};
use std::io::{self, Read};
use std::path::Path;
use std::sync::Arc;
use std::time::Duration;

use crate::config::Settings;
use crate::core::document::{Document, SourceType};
use crate::core::embedding::EmbeddingService;
use crate::core::rag::{RagConfig, RagEngine};
use crate::core::vector_store::VectorStore;
use crate::search::{ArxivSearcher, SearchProvider};
use crate::security::auth::AuthService;
use crate::security::crypto::CryptoService;
use crate::security::zero_trust::ZeroTrustConfig;
use crate::storage::QuestDbClient;

use super::{Commands, IngestSource, SecurityAction, TradingData};

/// Execute CLI command
pub async fn execute(cmd: Commands, settings: &Settings, verbose: bool) -> Result<()> {
    let term = Term::stdout();

    match cmd {
        Commands::Search { query, limit, format } => {
            search_command(&query, limit, &format, settings, verbose).await?;
        }

        Commands::Arxiv { query, max_results, ingest } => {
            arxiv_command(&query, max_results, ingest, settings, verbose).await?;
        }

        Commands::Ingest { source } => {
            ingest_command(source, settings, verbose).await?;
        }

        Commands::Trading { data } => {
            trading_command(data, settings).await?;
        }

        Commands::Serve { host, port, workers } => {
            term.write_line(&format!(
                "{} Starting server on {}:{}",
                style("[INFO]").cyan(),
                host,
                port
            ))?;
            // Server startup handled in bin/api.rs
        }

        Commands::Security { action } => {
            security_command(action, settings)?;
        }
    }

    Ok(())
}

async fn create_rag_engine(settings: &Settings) -> Result<RagEngine> {
    let embedding_service = EmbeddingService::new(
        &settings.search.embedding_model,
        settings.search.embedding_dimension,
    );

    let vector_store = VectorStore::new(
        &settings.database.qdrant_url,
        &settings.database.qdrant_collection,
        settings.search.embedding_dimension,
    )
    .await?;

    RagEngine::new(
        embedding_service,
        Arc::new(vector_store),
        RagConfig::default(),
    )
    .await
}

async fn search_command(
    query: &str,
    limit: usize,
    format: &str,
    settings: &Settings,
    verbose: bool,
) -> Result<()> {
    let term = Term::stdout();
    let pb = ProgressBar::new_spinner();
    pb.set_style(ProgressStyle::default_spinner().template("{spinner:.cyan} {msg}")?);
    pb.set_message("Searching knowledge base...");
    pb.enable_steady_tick(Duration::from_millis(100));

    let engine = create_rag_engine(settings).await?;
    let result = engine.query(query).await?;

    pb.finish_and_clear();

    match format {
        "json" => {
            let json = serde_json::json!({
                "query": query,
                "results": result.context_chunks.iter().map(|c| {
                    serde_json::json!({
                        "content": c.content,
                        "score": c.score,
                        "source": c.source_title
                    })
                }).collect::<Vec<_>>()
            });
            println!("{}", serde_json::to_string_pretty(&json)?);
        }
        "markdown" => {
            println!("# Search Results for: {}\n", query);
            for (i, chunk) in result.context_chunks.iter().enumerate() {
                println!("## Result {} (Score: {:.2})\n", i + 1, chunk.score);
                println!("{}\n", chunk.content);
                println!("*Source: {}*\n", chunk.source_title);
                println!("---\n");
            }
        }
        _ => {
            // Table format
            term.write_line(&format!(
                "\n{} Search results for: {}\n",
                style(">>>").green().bold(),
                style(query).cyan()
            ))?;

            for (i, chunk) in result.context_chunks.iter().take(limit).enumerate() {
                term.write_line(&format!(
                    "{} {} (score: {})",
                    style(format!("[{}]", i + 1)).yellow(),
                    style(&chunk.source_title).bold(),
                    style(format!("{:.2}", chunk.score)).dim()
                ))?;

                // Truncate content for display
                let content = if chunk.content.len() > 200 {
                    format!("{}...", &chunk.content[..200])
                } else {
                    chunk.content.clone()
                };
                term.write_line(&format!("    {}", style(content).dim()))?;
                term.write_line("")?;
            }

            if verbose {
                term.write_line(&format!(
                    "\n{} Total chunks: {}",
                    style("[DEBUG]").magenta(),
                    result.context_chunks.len()
                ))?;
            }
        }
    }

    Ok(())
}

async fn arxiv_command(
    query: &str,
    max_results: usize,
    ingest: bool,
    settings: &Settings,
    _verbose: bool,
) -> Result<()> {
    let term = Term::stdout();
    let pb = ProgressBar::new(max_results as u64);
    pb.set_style(ProgressStyle::default_bar()
        .template("{spinner:.cyan} [{bar:40.cyan/blue}] {pos}/{len} papers")?
        .progress_chars("=>-"));

    term.write_line(&format!(
        "\n{} Searching arXiv for: {}",
        style(">>>").green().bold(),
        style(query).cyan()
    ))?;

    let searcher = ArxivSearcher::new(max_results);
    let results = searcher.search(query, max_results).await?;

    pb.finish_and_clear();

    term.write_line(&format!(
        "{} Found {} papers\n",
        style("[OK]").green(),
        results.len()
    ))?;

    for (i, paper) in results.iter().enumerate() {
        term.write_line(&format!(
            "{} {}",
            style(format!("[{}]", i + 1)).yellow(),
            style(&paper.title).bold()
        ))?;
        term.write_line(&format!(
            "    Authors: {}",
            style(paper.authors.join(", ")).dim()
        ))?;
        term.write_line(&format!(
            "    arXiv: {}",
            style(&paper.arxiv_id).cyan()
        ))?;

        // Truncate summary
        let summary = if paper.summary.len() > 150 {
            format!("{}...", &paper.summary[..150])
        } else {
            paper.summary.clone()
        };
        term.write_line(&format!("    {}", style(summary).italic()))?;
        term.write_line("")?;
    }

    if ingest {
        term.write_line(&format!(
            "\n{} Ingesting papers into knowledge base...",
            style("[INFO]").cyan()
        ))?;

        let engine = create_rag_engine(settings).await?;
        let docs = engine.search_and_ingest_arxiv(query, max_results).await?;

        term.write_line(&format!(
            "{} Ingested {} papers",
            style("[OK]").green(),
            docs.len()
        ))?;
    }

    Ok(())
}

async fn ingest_command(source: IngestSource, settings: &Settings, verbose: bool) -> Result<()> {
    let term = Term::stdout();
    let engine = create_rag_engine(settings).await?;

    match source {
        IngestSource::Pdf { path, recursive } => {
            let path = Path::new(&path);

            if path.is_dir() {
                term.write_line(&format!(
                    "{} Processing PDFs in: {}",
                    style("[INFO]").cyan(),
                    path.display()
                ))?;

                let processor = crate::search::PdfProcessor::new();
                let docs = processor.process_directory(path).await?;

                for doc in docs {
                    engine.ingest_document(doc.clone()).await?;
                    term.write_line(&format!(
                        "  {} {}",
                        style("✓").green(),
                        doc.title
                    ))?;
                }
            } else {
                let doc = engine.ingest_pdf(path).await?;
                term.write_line(&format!(
                    "{} Ingested: {} ({} chunks)",
                    style("[OK]").green(),
                    doc.title,
                    doc.chunks.len()
                ))?;
            }
        }

        IngestSource::Url { url } => {
            term.write_line(&format!(
                "{} Fetching URL: {}",
                style("[INFO]").cyan(),
                url
            ))?;

            // Would implement URL fetching here
            term.write_line(&format!(
                "{} URL ingestion not yet implemented",
                style("[WARN]").yellow()
            ))?;
        }

        IngestSource::Text { title, file } => {
            let content = match file {
                Some(f) if f == "-" => {
                    let mut buffer = String::new();
                    io::stdin().read_to_string(&mut buffer)?;
                    buffer
                }
                Some(f) => std::fs::read_to_string(&f)?,
                None => {
                    term.write_line("Enter text (Ctrl+D to finish):")?;
                    let mut buffer = String::new();
                    io::stdin().read_to_string(&mut buffer)?;
                    buffer
                }
            };

            let doc = Document::new(&title, &content, SourceType::Manual);
            engine.ingest_document(doc.clone()).await?;

            term.write_line(&format!(
                "{} Ingested: {} ({} chars)",
                style("[OK]").green(),
                title,
                content.len()
            ))?;
        }
    }

    Ok(())
}

async fn trading_command(data: TradingData, settings: &Settings) -> Result<()> {
    let term = Term::stdout();
    let questdb = QuestDbClient::new(
        &settings.database.questdb_host,
        settings.database.questdb_port,
    )?;

    match data {
        TradingData::Gex { symbol, days, format } => {
            term.write_line(&format!(
                "\n{} GEX data for {} (last {} days)\n",
                style(">>>").green().bold(),
                style(&symbol).cyan(),
                days
            ))?;

            let gex_data = questdb.get_gex(&symbol, days).await?;

            if gex_data.is_empty() {
                term.write_line(&format!(
                    "{} No GEX data found for {}",
                    style("[WARN]").yellow(),
                    symbol
                ))?;
                return Ok(());
            }

            match format.as_str() {
                "json" => {
                    println!("{}", serde_json::to_string_pretty(&gex_data)?);
                }
                _ => {
                    println!("{:>12} {:>10} {:>12} {:>12}", "Strike", "GEX", "Call GEX", "Put GEX");
                    println!("{:-<50}", "");
                    for row in &gex_data {
                        println!(
                            "{:>12.2} {:>10.2} {:>12.2} {:>12.2}",
                            row.strike, row.gex, row.call_gex, row.put_gex
                        );
                    }
                }
            }
        }

        TradingData::Vanna { symbol, days } => {
            let vanna_data = questdb.get_vanna(&symbol, days).await?;

            if vanna_data.is_empty() {
                term.write_line(&format!(
                    "{} No Vanna data found for {}",
                    style("[WARN]").yellow(),
                    symbol
                ))?;
                return Ok(());
            }

            println!("\n{:>12} {:>10} {:>10} {:>10}", "Strike", "Vanna", "Delta", "IV");
            println!("{:-<50}", "");
            for row in &vanna_data {
                println!(
                    "{:>12.2} {:>10.4} {:>10.4} {:>10.2}%",
                    row.strike, row.vanna, row.delta, row.iv * 100.0
                );
            }
        }

        TradingData::Query { sql } => {
            let results = questdb.query(&sql).await?;
            println!("{}", serde_json::to_string_pretty(&results)?);
        }
    }

    Ok(())
}

fn security_command(action: SecurityAction, settings: &Settings) -> Result<()> {
    let term = Term::stdout();

    match action {
        SecurityAction::GenerateSecret => {
            let secret = CryptoService::generate_key();
            let hex: String = secret.iter().map(|b| format!("{:02x}", b)).collect();
            term.write_line(&format!(
                "{} Generated JWT secret:\n{}",
                style("[OK]").green(),
                style(&hex).cyan()
            ))?;
        }

        SecurityAction::TestZeroTrust { ip } => {
            let config = ZeroTrustConfig::default();
            let ip: std::net::IpAddr = ip.parse()?;

            let allowed = config.is_allowed(&ip);
            if allowed {
                term.write_line(&format!(
                    "{} IP {} is {}",
                    style("[OK]").green(),
                    ip,
                    style("ALLOWED").green().bold()
                ))?;
            } else {
                term.write_line(&format!(
                    "{} IP {} is {}",
                    style("[WARN]").yellow(),
                    ip,
                    style("BLOCKED").red().bold()
                ))?;
            }
        }

        SecurityAction::HashPassword { password } => {
            let auth = AuthService::new(settings.security.jwt_secret.clone(), 24);
            let hash = auth.hash_password(&password)?;
            term.write_line(&format!(
                "{} Password hash:\n{}",
                style("[OK]").green(),
                style(&hash).dim()
            ))?;
        }
    }

    Ok(())
}
