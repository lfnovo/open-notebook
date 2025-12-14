"""
Load Dutch word frequency data from OpenSubtitles corpus into SurrealDB.

This script loads Dutch word frequency data to help with CEFR classification.
High-frequency words typically indicate A1/A2 level, while low-frequency words
indicate C1/C2 level.

Data source: OpenSubtitles Dutch word frequency list
Format: CSV with columns: word, frequency, rank
"""
import asyncio
import csv
from pathlib import Path
from typing import List, Dict, Any

from loguru import logger

from open_notebook.domain.anki import DutchWordFrequency


async def load_dutch_frequencies_from_csv(csv_path: str):
    """
    Load Dutch word frequencies from CSV file.
    
    Expected CSV format:
    word,frequency,rank
    de,1234567,1
    een,987654,2
    ...
    """
    logger.info(f"Loading Dutch word frequencies from: {csv_path}")
    
    csv_file = Path(csv_path)
    if not csv_file.exists():
        logger.error(f"CSV file not found: {csv_path}")
        return
    
    words_to_insert = []
    count = 0
    
    try:
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            
            for row in reader:
                word_data = {
                    "word": row["word"].lower().strip(),
                    "frequency": int(row["frequency"]),
                    "rank": int(row["rank"]),
                }
                words_to_insert.append(word_data)
                count += 1
                
                # Batch insert every 1000 words
                if count % 1000 == 0:
                    await DutchWordFrequency.bulk_insert(words_to_insert)
                    logger.info(f"Inserted {count} words...")
                    words_to_insert = []
        
        # Insert remaining words
        if words_to_insert:
            await DutchWordFrequency.bulk_insert(words_to_insert)
        
        logger.info(f"Successfully loaded {count} Dutch word frequencies")
        
    except Exception as e:
        logger.error(f"Error loading word frequencies: {str(e)}")
        raise


async def generate_sample_data():
    """
    Generate sample Dutch word frequency data for testing.
    
    This creates a small sample dataset with common Dutch words.
    """
    logger.info("Generating sample Dutch word frequency data")
    
    sample_words = [
        # A1 level - very common words (rank 1-500)
        {"word": "de", "frequency": 5000000, "rank": 1},
        {"word": "het", "frequency": 4500000, "rank": 2},
        {"word": "een", "frequency": 4000000, "rank": 3},
        {"word": "is", "frequency": 3500000, "rank": 4},
        {"word": "en", "frequency": 3000000, "rank": 5},
        {"word": "van", "frequency": 2500000, "rank": 6},
        {"word": "in", "frequency": 2000000, "rank": 7},
        {"word": "te", "frequency": 1800000, "rank": 8},
        {"word": "dat", "frequency": 1600000, "rank": 9},
        {"word": "voor", "frequency": 1400000, "rank": 10},
        {"word": "ja", "frequency": 500000, "rank": 50},
        {"word": "nee", "frequency": 450000, "rank": 60},
        {"word": "hallo", "frequency": 400000, "rank": 70},
        {"word": "water", "frequency": 350000, "rank": 80},
        {"word": "eten", "frequency": 300000, "rank": 90},
        
        # A2 level - common words (rank 501-2000)
        {"word": "familie", "frequency": 100000, "rank": 800},
        {"word": "werken", "frequency": 95000, "rank": 850},
        {"word": "kopen", "frequency": 90000, "rank": 900},
        {"word": "huis", "frequency": 85000, "rank": 950},
        {"word": "school", "frequency": 80000, "rank": 1000},
        
        # B1 level - intermediate words (rank 2001-5000)
        {"word": "vergadering", "frequency": 30000, "rank": 3000},
        {"word": "studeren", "frequency": 28000, "rank": 3200},
        {"word": "vakantie", "frequency": 26000, "rank": 3400},
        {"word": "mening", "frequency": 24000, "rank": 3600},
        {"word": "ervaring", "frequency": 22000, "rank": 3800},
        
        # B2 level - upper intermediate (rank 5001-10000)
        {"word": "benadering", "frequency": 10000, "rank": 6000},
        {"word": "discussie", "frequency": 9500, "rank": 6500},
        {"word": "ontwikkeling", "frequency": 9000, "rank": 7000},
        {"word": "analyse", "frequency": 8500, "rank": 7500},
        {"word": "onderzoek", "frequency": 8000, "rank": 8000},
        
        # C1 level - advanced (rank 10001-20000)
        {"word": "implicatie", "frequency": 3000, "rank": 12000},
        {"word": "paradigma", "frequency": 2500, "rank": 14000},
        {"word": "coherentie", "frequency": 2000, "rank": 16000},
        {"word": "methodologie", "frequency": 1500, "rank": 18000},
        
        # C2 level - mastery (rank 20000+)
        {"word": "veelomvattend", "frequency": 500, "rank": 25000},
        {"word": "onontbeerlijk", "frequency": 400, "rank": 30000},
        {"word": "epistemologisch", "frequency": 300, "rank": 35000},
    ]
    
    try:
        await DutchWordFrequency.bulk_insert(sample_words)
        logger.info(f"Successfully inserted {len(sample_words)} sample words")
    except Exception as e:
        logger.error(f"Error inserting sample data: {str(e)}")
        raise


async def main():
    """Main function to run the loader."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Load Dutch word frequency data")
    parser.add_argument(
        "--csv",
        type=str,
        help="Path to CSV file with Dutch word frequencies",
    )
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Generate sample data for testing",
    )
    
    args = parser.parse_args()
    
    if args.sample:
        await generate_sample_data()
    elif args.csv:
        await load_dutch_frequencies_from_csv(args.csv)
    else:
        logger.error("Please provide either --csv <path> or --sample")
        parser.print_help()


if __name__ == "__main__":
    asyncio.run(main())
