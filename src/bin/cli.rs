//! Prior Notebook CLI

use anyhow::Result;
use clap::Parser;
use console::style;
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt};

use prior_notebook::{
    cli::{commands, Cli},
    config::Settings,
};

#[tokio::main]
async fn main() -> Result<()> {
    let cli = Cli::parse();

    // Initialize tracing based on verbosity
    let log_level = if cli.verbose { "debug" } else { "warn" };
    tracing_subscriber::registry()
        .with(tracing_subscriber::EnvFilter::new(log_level))
        .with(tracing_subscriber::fmt::layer().without_time())
        .init();

    // Print banner
    println!(
        r#"
{}
  ╔═══════════════════════════════════════════════════════════╗
  ║   ██████╗ ██████╗ ██╗ ██████╗ ██████╗                     ║
  ║   ██╔══██╗██╔══██╗██║██╔═══██╗██╔══██╗                    ║
  ║   ██████╔╝██████╔╝██║██║   ██║██████╔╝                    ║
  ║   ██╔═══╝ ██╔══██╗██║██║   ██║██╔══██╗                    ║
  ║   ██║     ██║  ██║██║╚██████╔╝██║  ██║                    ║
  ║   ╚═╝     ╚═╝  ╚═╝╚═╝ ╚═════╝ ╚═╝  ╚═╝                    ║
  ║                                                           ║
  ║   NOTEBOOK - Military-Grade RAG for Quant Trading         ║
  ╚═══════════════════════════════════════════════════════════╝
"#,
        style("").cyan()
    );

    // Load settings
    let settings = Settings::load().unwrap_or_else(|e| {
        eprintln!(
            "{} Failed to load config: {}. Using defaults.",
            style("[WARN]").yellow(),
            e
        );
        Settings::default()
    });

    // Execute command
    if let Err(e) = commands::execute(cli.command, &settings, cli.verbose).await {
        eprintln!("{} {}", style("[ERROR]").red().bold(), e);
        std::process::exit(1);
    }

    Ok(())
}
