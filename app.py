import pandas as pd
import tiktoken
import os
import streamlit as st
import re
import openai
import io
import time
import json



# Set the OpenAI model name (ensure the model is supported by your OpenAI subscription)
model = "gpt-4o-2024-11-20"

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

def process_with_gpt_in_batches(base_prompt, lines, model, type_compte, max_tokens=16000):
    remaining_lines = lines
    extracted_data = []
    
    while remaining_lines:
        prompt, remaining_lines, _ = prepare_prompt_with_limit(base_prompt, remaining_lines, model, 25, max_tokens)
        prompt += "\n"

        if type_compte == 'BS':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_bs)
        elif type_compte == 'P&L':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_pl)
        prompt += "\n"
        prompt += "Please provide the corresponding COA account for all the americain accounts above\n"
        messages = [{"role": "system", "content": "You are an assistant that provides structured JSON responses based on the schema."},
                    {"role": "user", "content": prompt}]
        response_format = {
    "type": "json_schema",
    "json_schema": {
        "name": "account_matching_response", 
        "schema": {
            "type": "object",  
            "properties": {
                "final_answer": {  
                    "type": "array", 
                    "items": {
                        "type": "object",
                        "properties": {
                            "account_number": {"type": "string"},
                            "label": {"type": "string"},
                            "coa_account": {"type": "string"},
                            "coa_label": {"type": "string"},
                            "justification": {"type": "string"}
                        },
                        "required": ["account_number", "label", "coa_account", "coa_label", "justification"],
                        "additionalProperties": False  
                    }
                }
            },
            "required": ["final_answer"],  # Seul "final_answer" est obligatoire
            "additionalProperties": False  # Aucun autre champ non spécifié n'est autorisé
        },
        "strict": True  # Active un contrôle strict du schéma
    }
}


        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                response_format = response_format,
                temperature=0.5,
                max_tokens=max_tokens
            )
            parsed_response = json.loads(response['choices'][0]['message']['content'])

                # Vérifier si "final_answer" contient une liste ou un seul objet
            final_answer = parsed_response["final_answer"]
            
            if isinstance(final_answer, list):
                # Si c'est une liste, étendre extracted_data avec ses éléments
                extracted_data.extend(final_answer)
            elif isinstance(final_answer, dict):
                # Si c'est un seul objet JSON, l'ajouter directement
                extracted_data.append(final_answer)
            else:
                raise ValueError("Unexpected format for 'final_answer'. Must be a list or dict.")

        except Exception as e:
            print(f"Error calling the API: {e}")
            break
        time.sleep(1)
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
def extract_from_list(response_input, acc_type):
    """
    Convert a JSON string or a list of dictionaries into a DataFrame. Each dictionary should contain keys:
    ['account_number', 'label', 'coa_account', 'coa_label', 'justification'].

    The returned DataFrame will have the following columns:
    ['n° de compte', 'Libelle', 'BS ou P&L', 'Compte COA', 'Libelle COA', 'Justification']

    Parameters:
    - response_input: A list of dictionaries extracted from the GPT responses.
    - acc_type: The account type ('BS' or 'P&L'), added as a column in the final DataFrame.

    Returns:
    A pandas DataFrame containing the structured mapping results.
    """

    data = []
    for item in response_input:
        try:
                # Extracting data from the dictionary
            numero = item['account_number']
            label = item['label']
            coa_account = item['coa_account']
            coa_label = item['coa_label']
            justification = item['justification']

                # Append the extracted information to the data list
            data.append([numero, label, acc_type, coa_account, coa_label, justification])
        except AttributeError:
            st.write("Error processing entry: ", item)

    # Create the DataFrame
    df = pd.DataFrame(
        data,
        columns=['n° de compte', 'Libelle', 'BS ou P&L', 'Compte COA', 'Libelle COA', 'Justification']
    )

    st.write(f"Finished processing {len(data)} {acc_type} accounts")
    return df
def remove_double_asterisks(df):
    # Pour chaque colonne du DataFrame
    for col in df.columns:
        # Vérifier si la colonne contient des données de type object (généralement des chaînes)
        if df[col].dtype == 'object':
            # Remplacer toutes les occurrences de '**' par '' (une chaîne vide)
            df[col] = df[col].str.replace('**', '', regex=False)
    return df
def normalize_number(num_str: str) -> str:
    """
    Normalize a numeric-like string by removing leading asterisks and spaces, and converting to an integer-like string if possible.

    Parameters:
    - num_str: The input string to normalize.

    Returns:
    - A normalized string representing the number, or the original string if not convertible.
    """
    try:
        # Strip leading and trailing spaces and remove leading '*'
        num_str = num_str.strip().lstrip('*').strip()

        # Attempt to convert the cleaned string to a number and back to string
        num = float(num_str)
        return str(int(num)) if num.is_integer() else str(num)
    except (ValueError, AttributeError):
        # Return the original string if conversion fails
        return num_str
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
        label="Download template",
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
        lines_bs = lines_bs.drop_duplicates()
        lines_pl = df[df[bs_pl_column] == 'P&L']
        del df

        if lines_bs.empty:
            st.warning("No Balance Sheet accounts found.")
            total_bs = 0
            lines_bs = []
        else:
            st.info(f"Found {len(lines_bs)} Balance Sheet accounts.")
            total_bs = len(lines_bs)
                # Prepare BS lines for GPT processing
            lines_bs = lines_bs.apply(lambda row: f"{row[numero_acc_column]},{row[label_column]},{row[bs_pl_column]}", axis=1).tolist()
            print(f"the lines_bs are {lines_bs}")
        if lines_pl.empty:
            st.warning("No Profit and Loss accounts found.")
            total_pl = 0
            lines_pl = []
        else:
            st.info(f"Found {len(lines_pl)} Profit and Loss accounts.")
            total_pl = len(lines_pl)
                # Prepare P&L lines for GPT processing
            lines_pl = lines_pl.apply(lambda row: f"{row[numero_acc_column]},{row[label_column]},{row[bs_pl_column]}", axis=1).tolist()
        if st.button("GO"):


            if  lines_bs:
                
                extracted_data_bs = process_with_gpt_in_batches(base_prompt, lines_bs, model, 'BS',max_tokens=16000)
                processed_numbers = {item['account_number'] for item in extracted_data_bs}
                #print(f"Processed numbers before update: {processed_numbers}")
            # We determine the lines that have not been processed yet
                remaining_lines_bs = [line for line in lines_bs if line.split(',')[0].strip() not in processed_numbers]
                #print(f"the remaining lines before loop are {remaining_lines_bs}")
                while remaining_lines_bs:
                    time.sleep(2)
                    # we process the remaining lines
                    new_data = process_with_gpt_in_batches(base_prompt, remaining_lines_bs, model, 'BS', max_tokens=16000)
                    extracted_data_bs.extend(new_data)
                   
                    # Add accounts numbers to the processed set
                    for item in new_data:
                        account_number = item['account_number']
                        if account_number not in processed_numbers:
                            processed_numbers.add(account_number)
                    #print(f"Processed numbers after update: {processed_numbers}")
                    # Mise à jour des lignes restantes
                    remaining_lines_bs = [line for line in lines_bs if line.split(',')[0].strip() not in processed_numbers]
                    #print(f"the remaining lines inside loop are {remaining_lines_bs}")
                df_bs = extract_from_list(extracted_data_bs, 'BS')
            else:
                df_bs = pd.DataFrame()
            
            if lines_pl:
                extracted_data_pl = process_with_gpt_in_batches(base_prompt, lines_pl, model, 'P&L',max_tokens=16000)
                processed_numbers = {item['account_number'] for item in extracted_data_pl}
                #print(f"Processed numbers before update: {processed_numbers}")
            # We determine the lines that have not been processed yet
                remaining_lines_pl = [line for line in lines_pl if line.split(',')[0].strip() not in processed_numbers]
                #print(f"the remaining lines before loop are {remaining_lines_pl}")
                while remaining_lines_pl:
                    time.sleep(2)
                    # we process the remaining lines
                    new_data = process_with_gpt_in_batches(base_prompt, remaining_lines_pl, model, 'P&L', max_tokens=16000)
                    extracted_data_pl.extend(new_data)
                   
                    # Add accounts numbers to the processed set
                    for item in new_data:
                        account_number = item['account_number']
                        if account_number not in processed_numbers:
                            processed_numbers.add(account_number)
                    #print(f"Processed numbers after update: {processed_numbers}")
                    # Mise à jour des lignes restantes
                    remaining_lines_pl = [line for line in lines_pl if line.split(',')[0].strip() not in processed_numbers]
                    #print(f"the remaining lines inside loop are {remaining_lines_pl}")
                df_pl = extract_from_list(extracted_data_pl, 'P&L')
            else:
                df_pl = pd.DataFrame()
            total_file = total_bs + total_pl
                # Combine results and prepare for download
            df = pd.concat([df_bs, df_pl], ignore_index=True)
            df_size = len(df)
            st.info(f"Successfully processed {df_size}/{total_file} accounts.")
            df = remove_double_asterisks(df)
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
      
if __name__ == "__main__":
    main()
