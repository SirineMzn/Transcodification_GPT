"""
Configuration module for the TranscoGPT application.
Contains all constants and configuration parameters.
"""
from typing import Final
import os
from dataclasses import dataclass

@dataclass
class APIConfig:
    MODEL: Final[str] = "gpt-4o-2024-11-20"
    MAX_TOKENS: Final[int] = 16000
    TEMPERATURE: Final[float] = 0.5
    COST_PER_1000_TOKENS_PROMPT: Final[float] = 0.00250
    COST_PER_1000_TOKENS_GEN: Final[float] = 0.01
    MAX_RETRIES: Final[int] = 3
    RETRY_DELAY: Final[int] = 2

@dataclass
class DataConfig:
    BASE_DIR: Final[str] = os.path.dirname(os.path.dirname(__file__))
    DATA_DIR: Final[str] = os.path.join(BASE_DIR, 'data')
    COA_FILE: Final[str] = os.path.join(DATA_DIR, 'COA_simplifié_TC2.xlsx')
    TEMPLATE_FILE: Final[str] = os.path.join(DATA_DIR, 'Template_TranscoGPT.xlsx')
    
    # Column indices (0-based)
    ACCOUNT_NUMBER_COL: Final[int] = 0
    LABEL_COL: Final[int] = 1
    TYPE_COL: Final[int] = 2
    
    MAX_FILE_SIZE_MB: Final[int] = 10
    BATCH_SIZE: Final[int] = 25

@dataclass
class LogConfig:
    LOG_DIR: Final[str] = os.path.join(os.path.dirname(__file__), 'logs')
    LOG_FORMAT: Final[str] = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
