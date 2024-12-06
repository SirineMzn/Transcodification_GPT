
# TranscoGPT by Supervizor

Automated Accounting Correspondence Tool

This project is a tool that allows matching foreign accounting accounts with French PCG accounts, developed in Python using the OpenAI API and Pandas for automation analysis.

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
- [Features](#features)
- [Configuration](#configuration)
- [License](#license)

## Installation

To install the dependencies, run the following commands:

```bash
# Clone the repository
git clone <project_url>

# Navigate to the project directory
cd project_name

# Install the dependencies
pip install -r requirements.txt
```

Make sure you have Python 3.8+ installed on your system.

## Usage

Here's how to use the project:

```bash
streamlit run main.py
```

For example, you can launch the Streamlit application to interact with the tool by uploading an Excel file containing the accounts to analyze.

## Features

- **Accounting Matching**: Match foreign accounts with French PCG accounts using OpenAI based on reference.
- **Automatic Label Cleaning**: Unifies the label format to ensure consistency.
- **User Interface via Streamlit**: Allows uploading an Excel file and displaying the matches.

## Configuration

Some configuration variables can be adjusted in the `.env` file or directly in Streamlit, for example:

- `API_key`: OpenAI API key used for API calls.
- `coa_file_path`: Path to the Excel file containing COA accounts.

Example configuration in a `.env` file:

```env
API_key=openai_api_key_here
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

# TranscoGPT by Supervizor

Outil de Correspondance Comptable Automatisée

Ce projet est un outil permettant de faire correspondre des comptes comptables étrangers avec des comptes PCG français, développé en Python en utilisant l'API OpenAI et Pandas pour l'automatisation des analyses.

## Table des Matières

- [Installation](#installation)
- [Utilisation](#utilisation)
- [Fonctionnalités](#fonctionnalités)
- [Configuration](#configuration)
- [Licence](#licence)

## Installation

Pour installer les dépendances, exécute les commandes suivantes :

```bash
# Clonez le dépôt
git clone <url_du_projet>

# Accédez au répertoire du projet
cd nom_du_projet

# Installez les dépendances
pip install -r requirements.txt
```

Assurez-vous d'avoir Python 3.8+ d'installé sur votre système.

## Utilisation

Voici comment utiliser le projet :

```bash
streamlit run main.py
```

Par exemple, vous pouvez lancer l'application Streamlit pour interagir avec l'outil en téléchargeant un fichier Excel contenant les comptes à analyser.

## Fonctionnalités

- **Correspondance Comptable** : Faire correspondre des comptes étrangers avec des comptes PCG français à l'aide d'OpenAI d'après le ref
- **Nettoyage Automatique des Libellés** : Unifie le format des libellés pour garantir la cohérence.
- **Interface Utilisateur via Streamlit** : Permet de télécharger un fichier Excel et d'afficher les correspondances.

## Configuration

Certaines variables de configuration peuvent être ajustées dans le fichier `.env` ou directement dans Streamlit, par exemple :

- `API_key` : Clé API OpenAI utilisée pour l'appel de l'API.
- `coa_file_path` : Chemin vers le fichier Excel contenant les comptes COA.

Exemple de configuration dans un fichier `.env` :

```env
API_key=openai_api_key_ici
```

## Licence

Ce projet est sous licence MIT - voir le fichier [LICENSE](LICENSE) pour plus de détails.
