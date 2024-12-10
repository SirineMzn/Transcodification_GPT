import pandas as pd
import tiktoken
import os
import streamlit as st
import re
import openai
import io
import time
# Set the model
model = "chatgpt-4o-latest"
# Set the API key
openai.api_key = st.secrets["API_key"]["openai_api_key"]
# Load the COA file
base_dir = os.path.dirname(__file__) 
coa_file_path = os.path.join(base_dir, 'data', 'COA_simplifié_TC2.xlsx')
coa = pd.read_excel(coa_file_path)
# fonction to unify account type in one format
def clean_text(text):
    # if not str convert value to string
    if not isinstance(text, str):
        text = str(text)
    
    # convert to lowercase
    text_cleaned = text.lower()
    
    # remplacements by first letter of the word
    if text.lower().startswith('b'):
        text_cleaned= 'BS'
    elif text.lower().startswith('p'):
        text_cleaned= 'P&L'
    return text_cleaned
coa['BS / P&L'] = coa['BS / P&L'].apply(clean_text)

coa_bs = coa[coa['BS / P&L'] == 'BS']
coa_pl = coa[coa['BS / P&L'] == 'P&L']
del coa
coa_bs = coa_bs.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()
coa_pl = coa_pl.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()

def estimate_prompt_cost(base_prompt, lines, model,acc_type, max_tokens=16000):
    encoding = tiktoken.get(model)
    remaining_lines = lines
    total_tokens = 0
    while remaining_lines:
        prompt, remaining_lines, prompt_tokens= prepare_prompt_with_limit(base_prompt, remaining_lines, model, 50, max_tokens)
        prompt += "\n"
        # Ajouter les comptes COA correspondants
        if acc_type == 'BS':
            prompt += "Voici les comptes BS à associer :\n" + "\n".join(coa_bs)
        elif acc_type == 'P&L':
            prompt += "Voici les comptes P&L à associer :\n" + "\n".join(coa_pl)

        total_tokens += len(encoding.encode(prompt))
        total_tokens += prompt_tokens
    cost_per_1000_tokens = 0.00250
    total_cost = (total_tokens / 1000) * cost_per_1000_tokens
    return total_cost
# Function to prepare the prompt with a limit of tokens and 50 libelles per prompt
def prepare_prompt_with_limit(base_prompt, lines, model, max_libelles =50, max_tokens = 16000):

    final_prompt = base_prompt
    remaining_lines = []
    count = 0
    for line in lines:
        
        if count > max_libelles:
            remaining_lines.append(line) 
        else:
            final_prompt += "\n" + line + "\n "
            count += 1    
    return final_prompt, remaining_lines

def process_with_gpt_in_batches(base_prompt, lines, model, type_compte, max_tokens=16000):
    remaining_lines = lines
    results = []
    extracted_data = []  # Liste pour stocker les données extraites
    block_pattern = r"\*\*Account Number: (.*?)\*\*.*?\*\*Label: (.*?)\*\*.*?\*\*COA Account: (.*?)\*\*.*?\*\*COA Label: (.*?)\*\*.*?\*\*Justification: (.*?)\*\*"

    while remaining_lines:
        # Préparer le prompt avec limite de tokens
        prompt, remaining_lines= prepare_prompt_with_limit(base_prompt, remaining_lines, model, 50, max_tokens=16000)
        prompt += "\n"
        
        # Ajouter les comptes COA correspondants
        if type_compte == 'BS':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_bs)
        elif type_compte == 'P&L':
            prompt += "Existing accounts in PCG :\n" + "\n".join(coa_pl)
        prompt += """Provide an accurate match with an account from the predetermined list by giving only and exactly the following response format for each account:
**Account Number: the account number**
**Label: the account label**
    **COA Account: the corresponding PCG account number**
    **COA Label: the corresponding PCG account label**
**Justification: explain in a maximum of 35 words why this account is the most appropriate.**
--- 
etc"""
        messages = [{"role": "user", "content": prompt}]
        try:
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                temperature=0.5,
                max_tokens=max_tokens,  # Limiter la réponse pour éviter de dépasser les quotas
            )
            
            # Ajouter la réponse brute à la liste des résultats
            results.append(response['choices'][0]['message']['content'])
            time.sleep(2)
            # Extraire les données correspondant au motif
            matches = re.findall(block_pattern, results[-1], re.DOTALL)
            for match in matches:
                extracted_data.append(match)
            
            
        except Exception as e:
            print(f"Erreur lors de l'appel API : {e}")
            break  # Arrêter en cas d'erreur

    # Afficher le nombre de blocs extraits
    print(f"Total number of extracted data : {len(extracted_data)}")
    #print(f"extracted data: {extracted_data}")
    # Retourner les résultats, les tokens totaux et les données extraites
    return extracted_data
base_prompt =     """Act as an expert in international accounting. Help me match a foreign accounting account (account number + label) to a French PCG account from a predetermined list.
The list contains either of two types of accounts:
BS (Balance Sheet): accounts related to the balance sheet.
P&L (Profit & Loss): accounts related to the income statement.
Analyze the following information:
Account Number: {account_number},Label: {label}, Type: {account_type}
"""
def extract_from_list(response_list,acc_type):
    """
    Extrait les informations d'une liste contenant un seul élément avec plusieurs blocs formatés
    et les place dans un DataFrame.

    :param response_list: Liste contenant une chaîne unique avec plusieurs blocs de données.
    :return: DataFrame avec les colonnes 'COA Account', 'COA Label', et 'Justification'.
    """
    
    if not response_list :
        raise ValueError("La liste est vide.")
    st.write(f"started processing {acc_type} accounts")
    response_list
        
    data = []
    for match in response_list:
        numero,label,coa_account, coa_label, justification = match
        data.append([numero.strip(),label.strip(),acc_type,coa_account.strip(), coa_label.strip(), justification.strip()])
                

    # Créer un DataFrame à partir des données extraites
    df = pd.DataFrame(
        data,
        columns=['n° de compte','Libelle','BS ou P&L','Compte COA', 'Libelle COA', 'Justification']
    )

    st.write(f"Finished processing {len(data)} of {acc_type} accounts")
    return df

# Main
def main():
    # Title 
    st.title("TranscoGPT by Supervizor AI")
    st.write("")
    st.markdown("""
    <div style="text-align: justify; font-size: 16px;">
        <img src="https://upload.wikimedia.org/wikipedia/en/a/a4/Flag_of_the_United_States.svg" width="20" style="vertical-align: middle; margin-right: 10px;">
        Welcome to <strong>TranscoGPT by Supervizor AI</strong>. This tool is designed to help you quickly and accurately map your foreign accounts to the Supervizor universal COA.
        Simply upload your Excel file, review the estimated costs, and let our GPT-based engine provide recommended mappings along with short justifications.
        Your data stays secure, and the entire process is protected by a password.
    </div>
""", unsafe_allow_html=True)
    st.write("")
    st.markdown("""
    <div style="text-align: justify; font-size: 16px;">
        <img src="https://upload.wikimedia.org/wikipedia/en/c/c3/Flag_of_France.svg" width="20" style="vertical-align: middle; margin-right: 10px;">
        Bienvenue sur <strong>TranscoGPT by Supervizor AI</strong>. Cet outil vous aide à mapper rapidement et précisément vos comptes étrangers sur le Supervizor universal COA.
        Il vous suffit d’importer votre fichier Excel, de vérifier l’estimation des coûts, et de laisser notre moteur à base de GPT vous fournir les mappings recommandés,
        accompagnés de brèves justifications. Vos données restent sécurisées, et l’ensemble du processus est protégé par un mot de passe.
    </div>
""", unsafe_allow_html=True)
    st.write("")


    # file path
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
            if lines_bs.empty:
                st.warning("No BS accounts found.")
                total_bs = 0
            else:
                st.info(f"Found {len(lines_bs)} BS accounts.")
                total_bs = len(lines_bs)
                lines_bs = lines_bs.apply(lambda row: f"""{row['N° de compte']},{row['Libellé']},{row['BS ou P&L']}""", axis=1).tolist()                


            if lines_pl.empty:
                st.warning("No P&L accounts found.")
                total_pl = 0
            else:
                st.info(f"Found {len(lines_pl)} P&L accounts.")
                lines_pl = lines_pl.apply(lambda row: f"""{row['N° de compte']} - {row['Libellé']} - {row['BS ou P&L']}""", axis=1).tolist()
                total_pl = len(lines_pl)
            
            if st.button("GO"):   
                if lines_bs:             
                    extracted_data_bs=process_with_gpt_in_batches(base_prompt, lines_bs, model,'BS', 16000)
                    
                    df_bs = extract_from_list(extracted_data_bs,'BS')
                else:
                    df_bs = pd.DataFrame()
                if lines_pl:
                    extracted_data_pl=process_with_gpt_in_batches(base_prompt, lines_pl, model,'P&L', 16000)

                    df_pl = extract_from_list(extracted_data_pl,'P&L')
                else:  
                    df_pl = pd.DataFrame()
                df = pd.concat([df_bs, df_pl], ignore_index=True)
                # Permettre à l'utilisateur de télécharger le fichier Excel traité
                output = io.BytesIO()
                df.to_excel(output, index=False, engine='xlsxwriter')
                output.seek(0)
                                    # Permettre à l'utilisateur de télécharger le fichier Excel traité
                st.success("Tap to download your file.")
                st.download_button(
                        label="Download processed file",
                        data=output,
                        file_name="output_traité.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                
            
        else:
            st.write("The file does not have columns : 'N° de compte', 'Libellé', 'BS ou P&L'.")
    

if __name__ == "__main__":
    main()