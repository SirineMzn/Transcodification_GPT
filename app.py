import pandas as pd
import tiktoken
import os
import streamlit as st
import re
base_dir = os.path.dirname(__file__)  # Le répertoire du script actuel
coa_file_path = os.path.join(base_dir, 'data', 'COA_simplifié_TC2.xlsx')
coa = pd.read_excel(coa_file_path)
# fonction to unify account type in one format
def clean_text(text):
    # if not str convert value to string
    if not isinstance(text, str):
        text = str(text)
    
    # convert to lowercase
    text_cleaned = text.lower()
    
    # replacements to apply
    replacements = {
        'BS': ['bs', 'b s'],
        'P&L': ['pnl', 'p l', 'pl', 'p and l']
    }
    # Remove special characters
    text_cleaned = re.sub(r'[^a-zA-Z\s]', ' ', text_cleaned)
    
    # Remove extra whitespaces
    text_cleaned = re.sub(r'\s+', ' ', text_cleaned).strip()
    # Replace each of bs and p&l with the key
    for replacement, patterns in replacements.items():
        # Créer une expression régulière pour les mots dans `patterns`
        pattern = r'\b(?:' + '|'.join(map(re.escape, patterns)) + r')\b'
        text_cleaned = re.sub(pattern, replacement, text_cleaned)
    

    
    return text_cleaned
coa['BS / P&L'] = coa['BS / P&L'].apply(clean_text)

coa_bs = coa[coa['BS / P&L'] == 'BS']
coa_pl = coa[coa['BS / P&L'] == 'P&L']
del coa
coa_bs = coa_bs.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()
coa_pl = coa_pl.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()

def prepare_prompt_with_limit(base_prompt, lines, model, max_libelles =50,max_tokens = 16000):
# Charger l'encodeur de tokens pour le modèle
    encoding = tiktoken.encoding_for_model(model)
    
    # Compter les tokens dans le prompt de base
    prompt_tokens = len(encoding.encode(base_prompt))
    final_prompt = base_prompt
    remaining_lines = []
    count = 0
    for line in lines:
        # Calculer la longueur de la ligne en tokens
        line_tokens = len(encoding.encode(line + "\n---\n"))
        
        # Vérifier si l'ajout de la ligne dépasse la limite maximale
        if prompt_tokens + line_tokens > max_tokens or count > max_libelles:
            remaining_lines.append(line)  # Conserver les lignes non ajoutées
        else:
            final_prompt += "\n" + line + "\n---\n"
            prompt_tokens += line_tokens
            count += 1

    
    return final_prompt, remaining_lines,prompt_tokens
# Traitement en lots avec GPT
def process_with_gpt_in_batches(base_prompt, lines, model, type_compte, max_tokens=16000):
    encoding = tiktoken.encoding_for_model(model)
    remaining_lines = lines
    total_tokens = 0

    while remaining_lines:
        prompt, remaining_lines, prompt_tokens = prepare_prompt_with_limit(base_prompt, remaining_lines, model, 50, max_tokens)
        prompt += "\n"
        
        # Ajouter les comptes COA correspondants
        if type_compte == 'BS':
            prompt += "Voici les comptes BS à associer :\n" + "\n".join(coa_bs)
        elif type_compte == 'P&L':
            prompt += "Voici les comptes P&L à associer :\n" + "\n".join(coa_pl)

        total_tokens += len(encoding.encode(prompt))
    return total_tokens
base_prompt =     """Act as an expert in international accounting. Help me match a foreign accounting account (account number + label) to a French PCG account from a predetermined list.
The list contains two types of accounts:
BS (Balance Sheet): accounts related to the balance sheet.
P&L (Profit & Loss): accounts related to the income statement.
Analyze the following information:
Account Number: {account_number}
Label: {label}
Type: {account_type}
Provide an accurate match with an account from the predetermined list by indicating:
COA Account: the corresponding PCG account number.
COA Label: the corresponding PCG account label.
Justification: explain in detail why this account is the most appropriate.
            """


# Main
def main():
    # Chemin du fichier
    file_uploaded = st.file_uploader("Please upload an Excel file only.", type=[ "xlsx"])
    if file_uploaded is not None:
        df = pd.read_excel(file_uploaded)
        df['BS ou P&L'] = df['BS ou P&L'].apply(clean_text)
            # Vérification des colonnes requises
        required_columns = ['N° de compte', 'Libellé', 'BS ou P&L']
            
        if all(column in df.columns for column in required_columns):
            lines_bs = df[df['BS ou P&L'] == 'BS']
            lines_pl = df[df['BS ou P&L'] == 'P&L']
            del df
            
            lines_bs = lines_bs.apply(lambda row: f"""{row['N° de compte']} - {row['Libellé']} - {row['BS ou P&L']}""", axis=1).tolist()
            lines_pl = lines_pl.apply(lambda row: f"""{row['N° de compte']} - {row['Libellé']} - {row['BS ou P&L']}""", axis=1).tolist()

            prompt_tokens_bs=process_with_gpt_in_batches(base_prompt, lines_bs, 'gpt-4','BS', 16000)
            prompt_tokens_pl=process_with_gpt_in_batches(base_prompt, lines_pl, 'gpt-4','P&L', 16000)
            cost_per_1000_tokens = 0.03
            total = prompt_tokens_bs + prompt_tokens_pl
            total_cost = (total / 1000) * cost_per_1000_tokens

            st.write(f"Estimated total number of tokens : {total}")
            st.write(f"Estimated total cost: {total_cost:.2f} USD")
        else:
            st.write("The file does not have columns : 'N° de compte', 'Libellé', 'BS ou P&L'.")
    

if __name__ == "__main__":
    main()