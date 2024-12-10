# TranscoGPT by Supervizor

## English README

### Introduction

**TranscoGPT by Supervizor** is a Streamlit application designed to help accountants and financial professionals easily map foreign accounts to French PCG (Plan Comptable Général) accounts. By leveraging OpenAI’s GPT models, it assists in the classification of both Balance Sheet (BS) and Profit & Loss (P&L) accounts into the most appropriate French PCG account, providing a clear justification for the choice.

### Features

- **Automatic Classification**: Automatically match foreign accounts (with account number and label) to the correct French PCG account.
- **BS and P&L Handling**: Supports both balance sheet (BS) and profit & loss (P&L) accounts.
- **Justifications**: Provides a concise explanation for why a certain PCG account was chosen.
- **Excel Input/Output**: Upload an Excel file containing the foreign accounts and retrieve a processed Excel file with PCG mappings.
- **Secure Access**: Includes password-protected access to the application, ensuring that only authorized users can utilize it.

### How It Works

1. **Upload Your Excel File**: Start by uploading your Excel file containing foreign accounts. Ensure the columns “N° de compte”, “Libellé”, and “BS ou P&L” are present.
2. **Process the Data**: The application uses GPT to analyze each account line and determines the best corresponding PCG account.  
3. **Download the Output**: Once processing is complete, download the resulting Excel file, now enriched with PCG mappings and justifications.

### Prerequisites

- **Python 3.9+**
- **Streamlit**
- **OpenAI API Key** (stored securely in `st.secrets`)
- **pandas**, **tiktoken**, **openai**, **re**, **io**, **xlsxwriter**, **time**

### Installation and Run

1. Install the required packages:
   ```bash
   pip install streamlit openai pandas tiktoken xlsxwriter
Set your OpenAI API key in Streamlit secrets:

bash
Copier le code
mkdir -p .streamlit
echo "[API_key]\nopenai_api_key = \"YOUR_API_KEY\"" > .streamlit/secrets.toml
Run the application:

bash
Copier le code
streamlit run app.py
Enter the password when prompted to access the interface.

Notes
The cost estimation for the GPT calls is based on token usage. The application provides an approximate cost before processing.
Ensure stable internet access since the classification relies on OpenAI’s API.




--------------------------------------------------------------
French README
Introduction
TranscoGPT by Supervizor est une application Streamlit conçue pour aider les comptables et les professionnels de la finance à mapper facilement des comptes étrangers sur les comptes du PCG (Plan Comptable Général) français. En s’appuyant sur les modèles GPT d’OpenAI, elle facilite la classification des comptes du bilan (BS) et du compte de résultat (P&L) vers le PCG français approprié, avec une justification claire pour chaque choix.

Fonctionnalités
Classification Automatique : Mise en correspondance automatique des comptes étrangers avec le compte PCG approprié.
Gestion BS et P&L : Prise en charge des comptes de bilan (BS) et de résultat (P&L).
Justifications Claires : Fournit une justification concise du choix du compte PCG.
Fichier Excel Entrant/Sortant : Importez votre fichier Excel contenant les comptes étrangers et récupérez un fichier Excel traité avec les mappings PCG.
Accès Sécurisé : Accès protégé par mot de passe, assurant que seuls les utilisateurs autorisés peuvent utiliser l’application.
Comment ça Marche
Importez Votre Fichier Excel : Téléversez votre fichier Excel contenant les comptes étrangers. Assurez-vous que les colonnes “N° de compte”, “Libellé” et “BS ou P&L” sont présentes.
Traitement des Données : L’application utilise GPT pour analyser chaque ligne de compte et déterminer le meilleur compte PCG correspondant.
Téléchargez le Résultat : Une fois le traitement terminé, téléchargez le fichier Excel enrichi des mappings PCG et des justifications.
Prérequis
Python 3.9+
Streamlit
Clé API OpenAI (stockée dans st.secrets)
pandas, tiktoken, openai, re, io, xlsxwriter, time
Installation et Exécution
Installez les dépendances nécessaires :

bash
Copier le code
pip install streamlit openai pandas tiktoken xlsxwriter
Définissez votre clé API OpenAI dans les secrets de Streamlit :

bash
Copier le code
mkdir -p .streamlit
echo "[API_key]\nopenai_api_key = \"VOTRE_CLE_API\"" > .streamlit/secrets.toml
Lancez l’application :

bash
Copier le code
streamlit run app.py
Saisissez le mot de passe lorsqu’il est demandé pour accéder à l’interface.

Remarques
L’estimation du coût pour les appels à GPT est basée sur l’utilisation de jetons. L’application fournit une estimation avant le lancement du traitement.
Assurez-vous d’avoir une connexion internet stable, car la classification fait appel à l’API d’OpenAI.