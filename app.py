import pandas as pd
import tiktoken
import os
import streamlit as st
import re
import openai
import io
import time

# Set the OpenAI model name (ensure the model is supported by your OpenAI subscription)
model = "chatgpt-4o-latest"

# Retrieve the OpenAI API key from Streamlit secrets
openai.api_key = st.secrets["API_key"]["openai_api_key"]

# Define paths to data files relative to the current script’s directory
base_dir = os.path.dirname(__file__) 
coa_file_path = os.path.join(base_dir, 'data', 'COA_simplifié_TC2.xlsx')
template_file_path = os.path.join(base_dir, 'data', 'Template_TranscoGPT.xlsx')

# Load the Excel template to be provided as a downloadable file
template = open(template_file_path, "rb").read()

# Load the COA (Chart of Accounts) file into a DataFrame
coa = pd.read_excel(coa_file_path)

def clean_text(text):
    """
    Normalize the account type textual values into a standardized format.
    - Convert non-string values to string.
    - Convert the text to lowercase.
    - If the text starts with 'b', classify as 'BS'.
    - If the text starts with 'p', classify as 'P&L'.
    """
    if not isinstance(text, str):
        text = str(text)
    text_cleaned = text.lower()
    if text_cleaned.startswith('b'):
        text_cleaned = 'BS'
    elif text_cleaned.startswith('p'):
        text_cleaned = 'P&L'
    return text_cleaned

# Apply the normalization function to the 'BS / P&L' column
coa['BS / P&L'] = coa['BS / P&L'].apply(clean_text)

# Split the COA into two separate lists: one for BS accounts and one for P&L accounts
coa_bs = coa[coa['BS / P&L'] == 'BS']
coa_pl = coa[coa['BS / P&L'] == 'P&L']

# Free memory from the initial COA DataFrame as we now have separate filtered lists
del coa

# Convert COA rows for BS and P&L into readable strings for the GPT prompt
coa_bs = coa_bs.apply(lambda row: f"{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}", axis=1).tolist()
coa_pl = coa_pl.apply(lambda row: f"{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}", axis=1).tolist()

def estimate_prompt_cost(base_prompt, lines, model, acc_type, max_tokens=16000):
    """
    Estimate the overall cost of processing a set of lines through the GPT model based on the token count.
    - base_prompt: The common introductory prompt text.
    - lines: The accounts data lines to process.
    - model: The GPT model name.
    - acc_type: The type of accounts being processed ('BS' or 'P&L').
    - max_tokens: The maximum number of tokens allowed per prompt block.
    
    The function:
    1. Iteratively prepares prompts with a limited number of accounts.
    2. Calculates the total tokens for all these prompt blocks.
    3. Estimates the cost based on a predefined rate per 1000 tokens.
    """
    encoding = tiktoken.get(model)
    remaining_lines = lines
    total_tokens = 0
    while remaining_lines:
        prompt, remaining_lines, prompt_tokens = prepare_prompt_with_limit(base_prompt, remaining_lines, model, 25, max_tokens)
        prompt += "\n"
        # Add relevant COA accounts list depending on the account type
        if acc_type == 'BS':
            prompt += "Voici les comptes BS à associer :\n" + "\n".join(coa_bs)
        elif acc_type == 'P&L':
            prompt += "Voici les comptes P&L à associer :\n" + "\n".join(coa_pl)

        # Count tokens for the constructed prompt
        total_tokens += len(encoding.encode(prompt))
        total_tokens += prompt_tokens

    # Define the cost per 1000 tokens (example rate)
    cost_per_1000_tokens = 0.00250
    total_cost = (total_tokens / 1000) * cost_per_1000_tokens
    return total_cost

def prepare_prompt_with_limit(base_prompt, lines, model, max_libelles=25, max_tokens=16000):
    """
    Build a prompt that includes a limited number of account lines to avoid exceeding token limits.
    - base_prompt: The base prompt text.
    - lines: The list of account lines to be appended.
    - max_libelles: Maximum number of lines (accounts) to add to the prompt.
    - max_tokens: Maximum tokens per prompt (not strictly enforced here, but good practice).
    
    Returns:
        final_prompt: The constructed prompt string.
        remaining_lines: The lines that were not included in this prompt (to be processed in subsequent calls).
        prompt_tokens: The count of tokens for the appended lines (optional for future calculations).
    """
    final_prompt = base_prompt
    remaining_lines = []
    count = 0

    for line in lines:
        if count > max_libelles:
            # If maximum number of lines is reached, push the rest into remaining_lines
            remaining_lines.append(line)
        else:
            final_prompt += "\n" + line + "\n "
            count += 1

    # For simplicity, we do not explicitly count prompt tokens here; 
    # if needed, token counting logic can be added.
    prompt_tokens = 0  
    return final_prompt, remaining_lines, prompt_tokens

def process_with_gpt_in_batches(base_prompt, lines, model, type_compte,language, max_tokens=16000):
    """
    Process a list of accounts in batches through the GPT model.
    
    Steps:
    1. Iteratively construct prompts, each containing up to a limited number of accounts.
    2. Add the appropriate COA account list (BS or P&L) to the prompt.
    3. Call the OpenAI API for each prompt and gather responses.
    4. Extract structured data (account number, label, matched COA account/label, and justification) using regex patterns.
    
    Parameters:
    - base_prompt (str): The prompt template used to guide the model.
    - lines (list[str]): The list of lines, each containing an account number, label, and type.
    - model (str): The GPT model name.
    - type_compte (str): 'BS' or 'P&L', indicating which type of accounts we are dealing with.
    - max_tokens (int): The maximum tokens allowed in a single response (to prevent overuse of tokens).
    
    Returns:
    A list of tuples, each containing extracted fields: 
    (account_number, label, matched_coa_account, matched_coa_label, justification).
    """
    remaining_lines = lines
    results = []
    extracted_data = []
    block_pattern = (
    r"\*\*Account Number[:\s*]*(.+?)(?=\*\*|\n|$)"
    r"\*\*Label[:\s*]*(.+?)(?=\*\*|\n|$)"
    r"\*\*COA Account[:\s*]*(.+?)(?=\*\*|\n|$)"
    r"\*\*COA Label[:\s*]*(.+?)(?=\*\*|\n|$)"
    r"\*\*Justification[:\s*]*(.+?)(?=\*\*|\n|$)"
)

    # Loop through all remaining lines, preparing and sending prompts in manageable batches
    while remaining_lines:
        prompt, remaining_lines, _ = prepare_prompt_with_limit(base_prompt, remaining_lines, model, 25, max_tokens=16000)
        prompt += "\n"

        # Append the appropriate COA account list to the prompt based on the account type
        if type_compte == 'BS':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_bs)
        elif type_compte == 'P&L':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_pl)

        # Provide formatting instructions for the GPT response
        prompt += """Provide an accurate match with an account from the predetermined list by giving only and exactly the following response format for each account:
**Account Number: the account number**
**Label: the account label**
    **COA Account: the corresponding PCG account number**
    **COA Label: the corresponding PCG account label**
**Justification: explain in a maximum of 35 words why this account is the most appropriate.**
--- 
"""
        prompt += f"respond in {language}"
        messages = [{"role": "user", "content": prompt}]
        try:
            # Call the OpenAI ChatCompletion endpoint
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_completion_tokens = max_tokens
                
            )

            # Append the raw response to results for potential debugging
            results.append(response['choices'][0]['message']['content'])
            time.sleep(1)  # Respect rate limits by adding a small delay
            print(results[-1])
            # Use regex to extract structured data from the response
            matches = re.findall(block_pattern, results[-1], re.DOTALL)
            for match in matches:
                extracted_data.append(match)
            
        except Exception as e:
            print(f"Error calling the API: {e}")
            break  # Stop processing if an error occurs

    print(f"Total number of extracted data : {len(extracted_data)}")
    return extracted_data

# Base prompt template to guide GPT toward mapping a foreign account to French PCG accounts
base_prompt = """Act as an expert in international accounting. Your objective is to establish a correspondence between each provided foreign accounting account (account number, label, and type) and an appropriate French PCG (Plan Comptable Général) account, based on a predefined list of accounts.
The list contains either of two types of accounts:
BS (Balance Sheet): accounts related to the balance sheet.
P&L (Profit & Loss): accounts related to the income statement.
For each foreign account provided, carefully analyze the following information:
Account Number: {account_number},Label: {label}, Type: {account_type}
Then, identify the corresponding French PCG account. Make sure to consider and fully process every account provided, without omitting any.
"""

def extract_from_list(response_list, acc_type):
    """
    Convert a list of extracted tuples into a DataFrame. Each tuple should contain:
    (account_number, foreign_label, corresponding_coa_account, corresponding_coa_label, justification).
    
    The returned DataFrame will have the following columns:
    ['n° de compte', 'Libelle', 'BS ou P&L', 'Compte COA', 'Libelle COA', 'Justification']
    
    Parameters:
    - response_list: A list of tuples extracted from the GPT responses.
    - acc_type: The account type ('BS' or 'P&L'), added as a column in the final DataFrame.
    
    Returns:
    A pandas DataFrame containing the structured mapping results.
    """
    

    st.write(f"Started processing {acc_type} accounts")

    data = []
    for match in response_list:
        numero, label, coa_account, coa_label, justification = match
        data.append([numero.strip(), label.strip(), acc_type, coa_account.strip(), coa_label.strip(), justification.strip()])

    df = pd.DataFrame(
        data,
        columns=['n° de compte', 'Libelle', 'BS ou P&L', 'Compte COA', 'Libelle COA', 'Justification']
    )

    st.write(f"Finished processing {len(data)} {acc_type} accounts")
    return df

def main():
    """
    Main Streamlit application logic:
    1. Display introduction and instructions to the user.
    2. Allow the user to download a template file.
    3. Enable the user to upload their own Excel file.
    4. Perform data validation and process the uploaded file.
    5. Once the 'GO' button is clicked:
       - Process BS accounts and P&L accounts separately via GPT.
       - Extract the results and combine them into a single DataFrame.
       - Provide the result as a downloadable Excel file.
    """
    # Application title and introduction
    st.title("TranscoGPT by Supervizor AI")
    st.write("")
    st.markdown("""
    <div style="text-align: justify; font-size: 16px;">
        <img src="https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg" width="20" style="vertical-align: middle; margin-right: 10px;">
        Welcome to <strong>TranscoGPT by Supervizor AI</strong>. This tool helps you map foreign accounts to our universal COA.
        Upload your Excel file, check the estimated cost, and let GPT provide recommended mappings with concise justifications.
        Your data remains secure throughout the process.
    </div>
    """, unsafe_allow_html=True)
    st.write("")
    st.markdown("""
    <div style="text-align: justify; font-size: 16px;">
        <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" width="20" style="vertical-align: middle; margin-right: 10px;">
        Bienvenue sur <strong>TranscoGPT by Supervizor AI</strong>. Cet outil vous aide à mapper rapidement et précisément vos comptes étrangers sur le COA universel de Supervizor.
        Importez votre fichier Excel, vérifiez l’estimation des coûts et laissez GPT fournir des mappings recommandés avec de brèves justifications.
        Vos données restent sécurisées tout au long du processus.
    </div>
    """, unsafe_allow_html=True)
    st.write("")

    # Allow the user to download the template file
    st.download_button(
        label="Download the template file",
        data=template,
        file_name="Template_TranscoGPT.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    # File uploader for the user's Excel file
    file_uploaded = st.file_uploader("Please upload an Excel file only.", type=["xlsx"])
    if file_uploaded is not None:
        df = pd.read_excel(file_uploaded)
        numero_acc_column = df.columns[0]
        label_column = df.columns[1]
        bs_pl_column = df.columns[2]
        df[bs_pl_column] = df[bs_pl_column].apply(clean_text)
        lines_bs = df[df[bs_pl_column] == 'BS']
        lines_pl = df[df[bs_pl_column] == 'P&L']
        del df

        if lines_bs.empty:
            st.warning("No BS accounts found.")
            total_bs = 0
            lines_bs = []
        else:
            st.info(f"Found {len(lines_bs)} BS accounts.")
            total_bs = len(lines_bs)
                # Prepare BS lines for GPT processing
            lines_bs = lines_bs.apply(lambda row: f"{row[numero_acc_column]},{row[label_column]},{row[bs_pl_column]}", axis=1).tolist()

        if lines_pl.empty:
            st.warning("No P&L accounts found.")
            total_pl = 0
            lines_pl = []
        else:
            st.info(f"Found {len(lines_pl)} P&L accounts.")
            total_pl = len(lines_pl)
                # Prepare P&L lines for GPT processing
            lines_pl = lines_pl.apply(lambda row: f"{row[numero_acc_column]} - {row[label_column]} - {row[bs_pl_column]}", axis=1).tolist()
                # displaying language options : "French" and "English"
        language = st.selectbox(
                    "Choose a language:", 
                    ( "English"),  # Options
                    index=0  # Default value is french
                )

            # Once user is ready, process the data
        if st.button("GO"):

                # Afficher la sélection
            st.write(f"You selected: {language}")

            if  lines_bs:
                extracted_data_bs = process_with_gpt_in_batches(base_prompt, lines_bs, model, 'BS',language,max_tokens=16000)
                df_bs = extract_from_list(extracted_data_bs, 'BS')
            else:
                df_bs = pd.DataFrame()

            if lines_pl:
                extracted_data_pl = process_with_gpt_in_batches(base_prompt, lines_pl, model, 'P&L',language,max_tokens=16000)
                df_pl = extract_from_list(extracted_data_pl, 'P&L')
            else:
                df_pl = pd.DataFrame()
            total_file = total_bs + total_pl
                # Combine results and prepare for download
            df = pd.concat([df_bs, df_pl], ignore_index=True)
            df_size = len(df)
            st.info(f"Finished processing {df_size}/{total_file} accounts.")

            output = io.BytesIO()
            df.to_excel(output, index=False, engine='xlsxwriter')
            output.seek(0)

            st.success("Tap to download your processed file.")
            st.download_button(
                    label="Download processed file",
                    data=output,
                    file_name="output_traduit.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

      
if __name__ == "__main__":
    main()
