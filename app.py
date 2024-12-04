import pandas as pd
import tiktoken
import os
import streamlit as st
import openai
import time
base_dir = os.path.dirname(__file__)  # Le répertoire du script actuel
coa_file_path = os.path.join(base_dir, 'data', 'COA_simplifié_TC2.xlsx')
coa = pd.read_excel(coa_file_path)
coa_bs = coa[coa['BS / P&L'] == 'BS']
coa_pl = coa[coa['BS / P&L'] == 'P&L']
del coa
coa_bs = coa_bs.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()
coa_pl = coa_pl.apply(lambda row: f"""{row['GL account']} - {row['Account Name']} - {row['BS / P&L']}""", axis=1).tolist()
file_path = os.path.join(base_dir, 'Test', "test_transco_v2.xlsx")  
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

        # Simuler l'envoi à GPT-3 (remplacez ici par votre appel réel à GPT)
        print(f"Le prompt envoyé à GPT-3 : {prompt}")
        total_tokens += len(encoding.encode(prompt))

    return total_tokens
base_prompt =     """Agis en tant qu'expert en comptabilité internationale. Aide-moi à associer un compte comptable étranger (n° de compte + libellé) à un compte PCG français provenant d'une liste prédéterminée. 
            La liste contient deux types de comptes :
            - **BS (Balance Sheet)** : comptes liés au bilan.
            - **P&L (Profit & Loss)** : comptes liés au compte de résultat.

            Analyse les informations suivantes :

            - **Numéro de compte** : {account_number}
            - **Libellé** : {label}
            - **Type** : {account_type}

            Fournis une correspondance précise avec un compte de la liste prédéterminée en indiquant :

            - **Compte COA** : numéro du compte PCG correspondant.
            - **Lib COA** : libellé du compte PCG correspondant.
            - **Justification** : explique en détail pourquoi ce compte est le plus approprié.
            """


# Main
def main():
    # Chemin du fichier

    try:
        print(f"Chargement du fichier : {file_path}")
        df = pd.read_excel(file_path)

        # Vérification des colonnes requises
        required_columns = ['N° de compte', 'Libellé', 'BS ou P&L']
        
        if all(column in df.columns for column in required_columns):
            lines_bs = df[df['BS ou P&L'] == 'BS']
            lines_pl = df[df['BS ou P&L'] == 'P&L']
            del df
            print("Fichier chargé avec succès!")
            lines_bs = lines_bs.apply(lambda row: f"""{row['N° de compte']} - {row['Libellé']} - {row['BS ou P&L']}""", axis=1).tolist()
            lines_pl = lines_pl.apply(lambda row: f"""{row['N° de compte']} - {row['Libellé']} - {row['BS ou P&L']}""", axis=1).tolist()
            prompt, remaining_lines,prompt_tokens = prepare_prompt_with_limit(base_prompt, lines_bs,'gpt-4', 50,16000)

            prompt_tokens=process_with_gpt_in_batches(base_prompt, lines_bs, 'gpt-4','BS', 16000)
            
            cost_per_1000_tokens = 0.03  # Remplacez par le coût réel par 1000 tokens
            
            total_cost = (prompt_tokens / 1000) * cost_per_1000_tokens

            print(f"Nombre total de tokens estimés : {prompt_tokens}")
            print(f"Coût estimé : {total_cost:.2f} USD")
        else:
            print("Le fichier ne contient pas les colonnes requises : 'N° de compte', 'Libellé', 'BS ou P&L'.")
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier : {e}")

if __name__ == "__main__":
    main()