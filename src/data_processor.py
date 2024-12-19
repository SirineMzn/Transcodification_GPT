"""
Data processing module for TranscoGPT application.
Handles all data transformation and validation operations.
"""
from typing import List, Dict, Tuple, Optional
import pandas as pd
import logging
from config import DataConfig
from utils import clean_text, normalize_number, DataValidationError

logger = logging.getLogger(__name__)

class DataProcessor:
    def __init__(self):
        """Initialize DataProcessor with COA data."""
        try:
            self.coa_data = self._load_coa()
            self.coa_bs, self.coa_pl = self._split_coa()
            logger.info("COA data loaded successfully")
        except Exception as e:
            logger.error(f"Failed to initialize DataProcessor: {str(e)}")
            raise

    def _load_coa(self) -> pd.DataFrame:
        """
        Load and prepare COA reference data.
        
        Returns:
            pd.DataFrame: Processed COA data
        """
        try:
            coa = pd.read_excel(DataConfig.COA_FILE)
            coa['BS / P&L'] = coa['BS / P&L'].apply(clean_text)
            return coa
        except Exception as e:
            logger.error(f"Error loading COA file: {str(e)}")
            raise

    def _split_coa(self) -> Tuple[List[str], List[str]]:
        """
        Split COA into BS and P&L lists.
        
        Returns:
            Tuple[List[str], List[str]]: BS and P&L account lists
        """
        coa_bs = self.coa_data[self.coa_data['BS / P&L'] == 'BS']
        coa_pl = self.coa_data[self.coa_data['BS / P&L'] == 'P&L']
        
        bs_list = coa_bs.apply(
            lambda row: f"{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}", 
            axis=1
        ).tolist()
        pl_list = coa_pl.apply(
            lambda row: f"{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}", 
            axis=1
        ).tolist()
        
        return bs_list, pl_list

    def process_input_file(self, file) -> Tuple[List[str], List[str], int, int]:
        """
        Process uploaded file and split into BS and P&L accounts.
        
        Args:
            file: Uploaded Excel file
            
        Returns:
            Tuple[List[str], List[str], int, int]: BS lines, P&L lines, BS count, P&L count
        """
        try:
            df = pd.read_excel(file)
            df = df.drop_duplicates()
            
            # Validate column count
            if len(df.columns) < 3:
                raise DataValidationError("File must contain at least 3 columns")
            
            # Process using column indices
            df.iloc[:, DataConfig.TYPE_COL] = df.iloc[:, DataConfig.TYPE_COL].apply(clean_text)
            
            # Split data
            lines_bs = df[df.iloc[:, DataConfig.TYPE_COL] == 'BS']
            lines_pl = df[df.iloc[:, DataConfig.TYPE_COL] == 'P&L']
            
            # Convert to required format
            bs_lines = self._convert_to_lines(lines_bs)
            pl_lines = self._convert_to_lines(lines_pl)
            
            return bs_lines, pl_lines, len(lines_bs), len(lines_pl)
            
        except Exception as e:
            logger.error(f"Error processing input file: {str(e)}")
            raise

    def _convert_to_lines(self, df: pd.DataFrame) -> List[str]:
        """
        Convert DataFrame rows to formatted strings.
        
        Args:
            df: Input DataFrame
            
        Returns:
            List[str]: Formatted account lines
        """
        return df.apply(
            lambda row: f"{row.iloc[DataConfig.ACCOUNT_NUMBER_COL]},"
                       f"{row.iloc[DataConfig.LABEL_COL]},"
                       f"{row.iloc[DataConfig.TYPE_COL]}", 
            axis=1
        ).tolist()

    def process_results(self, extracted_data: List[Dict], acc_type: str) -> pd.DataFrame:
        """
        Convert extracted data to DataFrame format.
        
        Args:
            extracted_data: List of processed account mappings
            acc_type: Account type ('BS' or 'P&L')
            
        Returns:
            pd.DataFrame: Processed results
        """
        data = []
        for item in extracted_data:
            try:
                data.append([
                    normalize_number(item['account_number']),
                    item['label'],
                    acc_type,
                    item['coa_account'],
                    item['coa_label'],
                    item['justification']
                ])
            except KeyError as e:
                logger.warning(f"Missing key in extracted data: {str(e)}")
                continue
        
        return pd.DataFrame(
            data,
            columns=['Account Number', 'Label', 'Account Type', 
                    'COA code', 'COA label', 'Justification']
        )

    def clean_final_output(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Clean and format final output DataFrame.
        
        Args:
            df: Input DataFrame
            
        Returns:
            pd.DataFrame: Cleaned DataFrame
        """
        # Remove double asterisks from all string columns
        for col in df.columns:
            if df[col].dtype == 'object':
                df[col] = df[col].str.replace('**', '', regex=False)
        
        # Normalize account numbers
        df['n° de compte'] = df['n° de compte'].apply(normalize_number)
        df['Compte COA'] = df['Compte COA'].apply(normalize_number)
        
        return df
