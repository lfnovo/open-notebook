import asyncio
import time
from typing import List, Optional

from loguru import logger
from pydantic import BaseModel
from surreal_commands import command


class TextProcessingInput(BaseModel):
    text: str
    operation: str = "uppercase"  # uppercase, lowercase, word_count, reverse
    delay_seconds: Optional[int] = None  # For testing async behavior

class TextProcessingOutput(BaseModel):
    success: bool
    original_text: str
    processed_text: Optional[str] = None
    word_count: Optional[int] = None
    processing_time: float
    error_message: Optional[str] = None

class DataAnalysisInput(BaseModel):
    numbers: List[float]
    analysis_type: str = "basic"  # basic, detailed
    delay_seconds: Optional[int] = None

class DataAnalysisOutput(BaseModel):
    success: bool
    analysis_type: str
    count: int
    sum: Optional[float] = None
    average: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    processing_time: float
    error_message: Optional[str] = None

@command("process_text", app="open_notebook")
async def process_text_command(input_data: TextProcessingInput) -> TextProcessingOutput:
    """
    Example command for text processing. Tests basic command functionality
    and demonstrates different processing types.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Processing text with operation: {input_data.operation}")
        
        # Simulate processing delay if specified
        if input_data.delay_seconds:
            await asyncio.sleep(input_data.delay_seconds)
        
        processed_text = None
        word_count = None
        
        if input_data.operation == "uppercase":
            processed_text = input_data.text.upper()
        elif input_data.operation == "lowercase":
            processed_text = input_data.text.lower()
        elif input_data.operation == "reverse":
            processed_text = input_data.text[::-1]
        elif input_data.operation == "word_count":
            word_count = len(input_data.text.split())
            processed_text = f"Word count: {word_count}"
        else:
            raise ValueError(f"Unknown operation: {input_data.operation}")
        
        processing_time = time.time() - start_time
        
        return TextProcessingOutput(
            success=True,
            original_text=input_data.text,
            processed_text=processed_text,
            word_count=word_count,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Text processing failed: {e}")
        return TextProcessingOutput(
            success=False,
            original_text=input_data.text,
            processing_time=processing_time,
            error_message=str(e)
        )

@command("analyze_data", app="open_notebook")
async def analyze_data_command(input_data: DataAnalysisInput) -> DataAnalysisOutput:
    """
    Example command for data analysis. Tests command with complex input/output
    and demonstrates error handling.
    """
    start_time = time.time()
    
    try:
        logger.info(f"Analyzing {len(input_data.numbers)} numbers with {input_data.analysis_type} analysis")
        
        # Simulate processing delay if specified
        if input_data.delay_seconds:
            await asyncio.sleep(input_data.delay_seconds)
        
        if not input_data.numbers:
            raise ValueError("No numbers provided for analysis")
        
        count = len(input_data.numbers)
        sum_value = sum(input_data.numbers)
        average = sum_value / count
        min_value = min(input_data.numbers)
        max_value = max(input_data.numbers)
        
        processing_time = time.time() - start_time
        
        return DataAnalysisOutput(
            success=True,
            analysis_type=input_data.analysis_type,
            count=count,
            sum=sum_value,
            average=average,
            min_value=min_value,
            max_value=max_value,
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Data analysis failed: {e}")
        return DataAnalysisOutput(
            success=False,
            analysis_type=input_data.analysis_type,
            count=0,
            processing_time=processing_time,
            error_message=str(e)
        )