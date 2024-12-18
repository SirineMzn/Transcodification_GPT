"""
UI components module for TranscoGPT application.
Handles all Streamlit UI elements and interactions.
"""
import streamlit as st
from typing import Tuple, Optional, Any
import pandas as pd
import io
from config import DataConfig, APIConfig
import logging

logger = logging.getLogger(__name__)

class UI:
    def __init__(self):
        """Initialize UI components."""
        self.setup_page()

    def setup_page(self):
        """Configure page layout and style."""
        st.set_page_config(
            page_title="TranscoGPT by Supervizor AI",
            layout="wide"
        )
        self.display_header()

    def display_header(self):
        """Display application header and introduction."""
        st.title("TranscoGPT by Supervizor AI")
        st.write("")
        
        # English introduction
        st.markdown("""
        <div style="text-align: justify; font-size: 16px;">
            <img src="https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg" 
                 width="20" style="vertical-align: middle; margin-right: 10px;">
            Welcome to <strong>TranscoGPT by Supervizor AI</strong>. This tool helps you map foreign 
            accounts to our universal COA. Upload your Excel file, check the estimated cost, and let 
            GPT provide recommended mappings with concise justifications. Your data remains secure 
            throughout the process.
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        
        # French introduction
        st.markdown("""
        <div style="text-align: justify; font-size: 16px;">
            <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" 
                 width="20" style="vertical-align: middle; margin-right: 10px;">
            Bienvenue sur <strong>TranscoGPT by Supervizor AI</strong>. Cet outil vous aide à mapper 
            rapidement et précisément vos comptes étrangers sur le COA universel de Supervizor. 
            Importez votre fichier Excel, vérifiez l'estimation des coûts et laissez GPT fournir 
            des mappings recommandés avec de brèves justifications. Vos données restent sécurisées 
            tout au long du processus.
        </div>
        """, unsafe_allow_html=True)
        
        st.write("")

    def display_template_download(self, template: bytes):
        """
        Display template download button.
        
        Args:
            template: Template file content
        """
        st.download_button(
            label="Download template",
            data=template,
            file_name="Template_TranscoGPT.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def file_uploader(self) -> Optional[Any]:
        """
        Display file upload widget.
        
        Returns:
            Optional[Any]: Uploaded file object
        """
        return st.file_uploader(
            "Please upload an Excel file only.", 
            type=["xlsx"]
        )

    def display_account_summary(self, bs_count: int, pl_count: int):
        """
        Display summary of found accounts.
        
        Args:
            bs_count: Number of BS accounts
            pl_count: Number of P&L accounts
        """
        if bs_count == 0:
            st.warning("No Balance Sheet accounts found.")
        else:
            st.info(f"Found {bs_count} Balance Sheet accounts.")
            
        if pl_count == 0:
            st.warning("No Profit and Loss accounts found.")
        else:
            st.info(f"Found {pl_count} Profit and Loss accounts.")

    def display_cost_estimate(self, cost: float):
        """
        Display estimated processing cost.
        
        Args:
            cost: Estimated cost in dollars
        """
        st.info(f"Estimated cost: ${cost:.2f}")

    def display_progress(self, current: int, total: int):
        """
        Display processing progress.
        
        Args:
            current: Current progress
            total: Total items to process
        """
        progress_bar = st.progress(0)
        progress = current / total if total > 0 else 0
        progress_bar.progress(progress)
        st.write(f"Processing: {current}/{total} accounts")

    def display_results(self, df: pd.DataFrame, total_accounts: int):
        """
        Display processing results and download button.
        
        Args:
            df: Processed results DataFrame
            total_accounts: Total number of accounts processed
        """
        df_size = len(df)
        st.info(f"Successfully processed {df_size}/{total_accounts} accounts.")
        
        # Prepare download file
        output = io.BytesIO()
        df.to_excel(output, index=False, engine='xlsxwriter')
        output.seek(0)
        
        st.success("Tap to download your completed file.")
        st.download_button(
            label="Download processed file",
            data=output,
            file_name="transco_gpt.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    def display_error(self, error_message: str):
        """
        Display error message.
        
        Args:
            error_message: Error message to display
        """
        st.error(f"Error: {error_message}")
        logger.error(error_message)
