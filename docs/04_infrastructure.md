# Infrastructure

## 1. Serveur hôte

| Attribut | Valeur |
|---|---|
| Nom | `WWDBA01-D01` |
| FQDN | `WWDBA01-D01.groupesifa.com` |
| OS | Windows Server 2019 Datacenter (Build 17763) |
| Hyperviseur | Hyper-V (VM) |
| Python | 3.10.6 |
| Shell | PowerShell 5.1 |

---

## 2. SQL Server 2022

### Instances installées

| Instance | Nom service | Édition | Statut |
|---|---|---|---|
| `MSSQLSERVER` | MSSQLSERVER | *(à vérifier)* | — |
| `MSSQLSERVER2022` | MSSQLSERVER2022 | Developer Edition | **Utilisée** |

### Connexion

```
Serveur  : localhost\MSSQLSERVER2022
Base     : RetraitesOpenData
Compte   : sa
Mot de passe : récupéré depuis Azure Key Vault (secret "SQL-SACredential")
Port     : 1433 (défaut)
```

Depuis sqlcmd :
```powershell
$pwd = (Get-AzKeyVaultSecret -VaultName sifa-vault1 -Name SQL-SACredential -AsPlainText)
sqlcmd -S "localhost\MSSQLSERVER2022" -U sa -P $pwd -d RetraitesOpenData
```

### Bases de données créées

| Base | Usage | Script de création |
|---|---|---|
| `RetraitesOpenData` | Base principale du projet | `sql/create_database.sql` + `sql/create_enrichissements.sql` |

### Pilote ODBC requis

Le driver **ODBC Driver 18 for SQL Server** doit être installé pour la connexion Python via pyodbc.  
Vérification :
```powershell
Get-OdbcDriver -Name "ODBC Driver 18 for SQL Server" -ErrorAction SilentlyContinue
```
Téléchargement si absent : https://learn.microsoft.com/fr-fr/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## 3. Azure Key Vault

### Paramètres

| Attribut | Valeur |
|---|---|
| Nom | `sifa-vault1` |
| URL | `https://sifa-vault1.vault.azure.net/` |
| Tenant Azure AD | `90b590b6-5ccc-471c-a0b0-8ee1389e07c7` (SIFA) |
| Modèle d'accès | **Access Policies** (pas Azure RBAC) |

> **Important :** le vault est en mode **Access Policies**. Les role assignments Azure RBAC (IAM) sont ignorés pour le data plane dans ce mode. Seules les Access Policies contrôlent l'accès aux secrets.

### Secrets gérés

| Nom du secret | Contenu | Utilisé par |
|---|---|---|
| `SQL-SACredential` | Mot de passe du compte `sa` SQL Server | `src/vault.py` → `src/db.py` |
| `TenantID` | Tenant Azure AD (référence) | `scripts/setup_credentials.ps1` |
| `datasvc-clientid` | App ID de `sp-sifa-datasvc` (référence) | `scripts/setup_credentials.ps1` |
| `datasvc-secret-01` | Secret de `sp-sifa-datasvc` | `scripts/setup_credentials.ps1` → registre Windows |

### Access Policy assignée à `sp-sifa-datasvc`

| Permission | Valeur |
|---|---|
| Secrets — Get | ✓ |
| Secrets — List | ✓ |
| Clés, Certificats | ✗ |

### Authentification depuis ce serveur (runtime)

**Aucune session Azure interactive n'est nécessaire au démarrage normal.**

`src/vault.py` utilise `ClientSecretCredential` avec les paramètres suivants :

```
AZURE_TENANT_ID     ← .env (identifiant public)
AZURE_CLIENT_ID     ← .env (identifiant public)
AZURE_CLIENT_SECRET ← winreg HKLM (écrit une seule fois par scripts/setup_credentials.ps1)
```

Le script `scripts/setup_credentials.ps1` est la seule opération qui nécessite une connexion Azure interactive (`Connect-AzAccount`). Il s'exécute **une seule fois** lors de l'installation, puis lit les 3 credentials depuis le vault et écrit `AZURE_CLIENT_SECRET` dans le registre Windows.

---

## 4. Souscriptions Azure

| Nom | ID | Usage |
|---|---|---|
| Abonnement Azure 1 | `47b9d7c1-4229-4c02-b8b8-6d89a4a7ee38` | Défaut configuré — contient `sifa-vault1` |
| sub-integration-platform-sifa-dev | `a51c1ff2-e098-4af0-a31c-6a8c26ceee1a` | Environnement de développement |
| sub-integration-platform-sifa-prd | `d8034c78-e089-4b8a-bdb3-812540eb6db1` | Production |
| sub-integration-platform-sifa-stg | `0e940b54-b4e9-459f-979d-fb67db5b1dd5` | Staging |

---

## 5. Réseau

### Accès Jupyter depuis le réseau local

Jupyter est lancé en écoute sur `0.0.0.0:8888`. Pour accéder depuis un poste client :

```
http://WWDBA01-D01.groupesifa.com:8888
```

**Prérequis réseau :**
- Port 8888 TCP ouvert sur le pare-feu Windows de WWDBA01-D01 vers le réseau interne
- Si pare-feu Windows bloquant :
  ```powershell
  New-NetFirewallRule -DisplayName "Jupyter Notebook" -Direction Inbound `
      -Protocol TCP -LocalPort 8888 -Action Allow -Profile Domain,Private
  ```

### Accès API externe

Les URL suivantes doivent être accessibles en sortie HTTPS :

| URL | Usage |
|---|---|
| `https://data.assuranceretraite.fr` | API OpenDataSoft CNAV |
| `https://api.insee.fr` | INSEE API BDM |
| `https://sifa-vault1.vault.azure.net` | Azure Key Vault |
| `https://login.microsoft.com` | Authentification Azure AD |
| `https://management.azure.com` | Az PowerShell — setup initial uniquement |
| `https://graph.microsoft.com` | Création Service Principal — admin AD uniquement |

---

## 6. Modules Az PowerShell installés

Installés dans `$env:USERPROFILE\Documents\WindowsPowerShell\Modules\` (scope `CurrentUser`) :

| Module | Version | Usage |
|---|---|---|
| Az.Accounts | ≥ 3.x | Authentification Azure |
| Az.KeyVault | ≥ 6.x | Lecture secrets Key Vault |
| Az.Resources | ≥ 9.x | Création Service Principal (admin) |

---

## 7. Packages Python installés

Voir `requirements.txt`. Groupe fonctionnel :

| Groupe | Packages |
|---|---|
| Data | pandas, numpy, pyarrow |
| Ingestion | requests, python-dotenv, openpyxl |
| Visualisation | matplotlib, seaborn, plotly |
| Jupyter | jupyter, notebook, ipykernel |
| Modélisation | statsmodels, prophet, scikit-learn |
| Azure | azure-identity, azure-keyvault-secrets |
| SQL Server | pyodbc, sqlalchemy |
| Certificats SSL | pip-system-certs |

> **`pip-system-certs`** est obligatoire en environnement corporate avec proxy TLS (inspection SSL). Il injecte le magasin de certificats Windows dans les requêtes HTTPS Python, évitant les erreurs `SSL: CERTIFICATE_VERIFY_FAILED` vers `sifa-vault1.vault.azure.net`.
