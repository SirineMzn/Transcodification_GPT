"""
Main application module for TranscoGPT.
Coordinates all components and handles the main application flow.
"""
import streamlit as st
import asyncio
import logging
from typing import Optional, Tuple
import pandas as pd

from config import DataConfig,APIConfig
from utils import setup_logging, validate_file
from data_processor import DataProcessor
from api_handler import APIHandler
from ui_components import UI
import time
logger = logging.getLogger(__name__)

class TranscoGPT:
    def __init__(self):
        """Initialize TranscoGPT application."""
        setup_logging()
        self.ui = UI()
        self.data_processor = DataProcessor()
        self.api_handler = APIHandler()
        
        # Load template file
        with open(DataConfig.TEMPLATE_FILE, "rb") as f:
            self.template = f.read()

    async def process_accounts(self, lines: list, acc_type: str) -> list:
        """
        Process accounts through API in batches.
        
        Args:
            lines: List of account lines to process
            acc_type: Account type ('BS' or 'P&L')
            
        Returns:
            list: Processed account data
        """
        if not lines:
            return []

        processed_data = []
        total_lines = len(lines)
        processed_count = 0

        for i in range(0, total_lines, DataConfig.BATCH_SIZE):
            batch = lines[i:i + DataConfig.BATCH_SIZE]
            try:
                coa_accounts = (self.data_processor.coa_bs if acc_type == 'BS' 
                              else self.data_processor.coa_pl)
                
                result = await self.api_handler.process_batch(
                    self.create_prompt(batch),
                    coa_accounts
                )
                
                if result:
                    processed_data.extend(result)
                    
                processed_count += len(batch)
                self.ui.display_progress(processed_count, total_lines)
                
            except Exception as e:
                logger.error(f"Error processing batch: {str(e)}")
                continue

        return processed_data

    def create_prompt(self, batch: list) -> str:
        """
        Create prompt for API processing.
        
        Args:
            batch: Batch of accounts to process
            
        Returns:
            str: Formatted prompt
        """
        base_prompt = """Act as an expert in international accounting. Your objective is to establish 
        a correspondence between each provided foreign accounting account (account number, label, and type) 
        and an appropriate French PCG (Plan Comptable Général) account, based on a predefined list of accounts."""
        
        return base_prompt + "\n\nAccounts to process:\n" + "\n".join(batch)

    async def run(self):
        """Main application flow."""
        try:
            # Display template download button
            self.ui.display_template_download(self.template)
            
            # File upload
            uploaded_file = self.ui.file_uploader()
            if uploaded_file is None:
                return

            # Validate uploaded file
            is_valid, error_message = validate_file(uploaded_file)
            if not is_valid:
                self.ui.display_error(error_message)
                return

            # Process input file
            bs_lines, pl_lines, bs_count, pl_count = self.data_processor.process_input_file(uploaded_file)
            self.ui.display_account_summary(bs_count, pl_count)

            # Calculate and display cost estimate
            total_cost = self.calculate_cost(bs_lines, pl_lines)
            self.ui.display_cost_estimate(total_cost)

            # Process accounts when user clicks GO
            if st.button("GO"):
                # Process BS accounts
                if bs_lines:
                    bs_data = await self.process_accounts(bs_lines, 'BS')
                    processed_numbers = {item['account_number'] for item in bs_data}
                    
                    # Check for unprocessed BS accounts
                    remaining_bs_lines = [line for line in bs_lines 
                                        if line.split(',')[0].strip() not in processed_numbers]
                    
                    while remaining_bs_lines:
                        time.sleep(APIConfig.RETRY_DELAY)
                        new_data = await self.process_accounts(remaining_bs_lines, 'BS')
                        bs_data.extend(new_data)
                        
                        # Update processed accounts
                        for item in new_data:
                            processed_numbers.add(item['account_number'])
                        
                        # Update remaining lines
                        remaining_bs_lines = [line for line in bs_lines 
                                            if line.split(',')[0].strip() not in processed_numbers]
                    
                    bs_df = self.data_processor.process_results(bs_data, 'BS')
                else:
                    bs_df = pd.DataFrame()

                # Process P&L accounts
                if pl_lines:
                    pl_data = await self.process_accounts(pl_lines, 'P&L')
                    processed_numbers = {item['account_number'] for item in pl_data}
                    
                    # Check for unprocessed P&L accounts
                    remaining_pl_lines = [line for line in pl_lines 
                                        if line.split(',')[0].strip() not in processed_numbers]
                    
                    while remaining_pl_lines:
                        time.sleep(APIConfig.RETRY_DELAY)
                        new_data = await self.process_accounts(remaining_pl_lines, 'P&L')
                        pl_data.extend(new_data)
                        
                        # Update processed accounts
                        for item in new_data:
                            processed_numbers.add(item['account_number'])
                        
                        # Update remaining lines
                        remaining_pl_lines = [line for line in pl_lines 
                                            if line.split(',')[0].strip() not in processed_numbers]
                    
                    pl_df = self.data_processor.process_results(pl_data, 'P&L')
                else:
                    pl_df = pd.DataFrame()

                # Combine and clean results
                final_df = pd.concat([bs_df, pl_df], ignore_index=True)
                final_df = self.data_processor.clean_final_output(final_df)

                # Display results and processing summary
                total_processed = len(final_df)
                total_accounts = bs_count + pl_count
                self.ui.display_results(final_df, total_accounts)
                st.info(f"Successfully processed {total_processed}/{total_accounts} accounts.")

        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            self.ui.display_error(str(e))


    def calculate_cost(self, bs_lines: list, pl_lines: list) -> float:
        """
        Calculate estimated processing cost.
        
        Args:
            bs_lines: BS account lines
            pl_lines: P&L account lines
            
        Returns:
            float: Estimated cost
        """
        total_accounts = len(bs_lines) + len(pl_lines)
        output_tokens = total_accounts * 120
        prompt_cost = (output_tokens / 1000) * APIConfig.COST_PER_1000_TOKENS_PROMPT
        gen_cost = (output_tokens / 1000) * APIConfig.COST_PER_1000_TOKENS_GEN
        return prompt_cost + gen_cost

if __name__ == "__main__":
    app = TranscoGPT()
    asyncio.run(app.run())
