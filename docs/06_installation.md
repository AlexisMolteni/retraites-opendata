# Guide d'Installation

> **Environnement cible :** Windows Server 2019 — `WWDBA01-D01.groupesifa.com`
> **Durée estimée :** 30 à 60 minutes (hors téléchargement des données)

---

## Prérequis

| Composant | Version | Vérification |
|---|---|---|
| Python | 3.10 | `python --version` |
| SQL Server 2022 | Instance `MSSQLSERVER2022` | `sqlcmd -S localhost\MSSQLSERVER2022 -Q "SELECT @@VERSION"` |
| ODBC Driver 18 | for SQL Server | `Get-OdbcDriver -Name "ODBC Driver 18*"` |
| Az PowerShell | Az.Accounts 3.x | `Get-Module Az.Accounts -ListAvailable` |
| Accès internet | — | Vers `data.assuranceretraite.fr`, `sifa-vault1.vault.azure.net` |

### Installer ODBC Driver 18 (si absent)

```powershell
$url = "https://go.microsoft.com/fwlink/?linkid=2249006"
Invoke-WebRequest -Uri $url -OutFile "$env:TEMP\msodbcsql18.msi"
Start-Process msiexec.exe -Wait -ArgumentList "/i $env:TEMP\msodbcsql18.msi /quiet IACCEPTMSODBCSQLLICENSETERMS=YES"
```

### Installer Az PowerShell (si absent)

```powershell
Install-Module Az.Accounts, Az.KeyVault -Scope CurrentUser -Force -Repository PSGallery
```

---

## Étape 1 — Récupérer le projet

```powershell
cd d:\DEV
git clone <url-du-dépôt> retraites-opendata
cd retraites-opendata
```

---

## Étape 2 — Environnement virtuel Python

```powershell
cd d:\DEV\retraites-opendata
python -m venv .venv
```

> Si `Activate.ps1` est bloqué par la politique d'exécution :
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

---

## Étape 3 — Installer les dépendances Python

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Le package `pip-system-certs` est inclus dans les dépendances — il permet au SDK Azure d'utiliser le magasin de certificats Windows (nécessaire en environnement corporate avec proxy SSL).

**Durée :** 5 à 15 minutes (Prophet compile des extensions C).

### Vérification

```powershell
.venv\Scripts\python.exe -c "import pandas, sqlalchemy, azure.keyvault.secrets; print('OK')"
```

---

## Étape 4 — Configurer le fichier `.env`

```powershell
Copy-Item .env.example .env
```

Le `.env` ne contient **aucun secret**. Il faut uniquement renseigner `AZURE_TENANT_ID` et `AZURE_CLIENT_ID` (identifiants publics du SP `sp-sifa-datasvc`) :

```env
AZURE_TENANT_ID=90b590b6-5ccc-471c-a0b0-8ee1389e07c7
AZURE_CLIENT_ID=2ae721a6-4ae1-45b3-8bb3-dba87845a23f
```

Les autres valeurs sont déjà correctes dans `.env.example`.

---

## Étape 5 — Injecter `AZURE_CLIENT_SECRET` dans le registre Windows

Cette étape est la seule qui nécessite une connexion Azure interactive. Elle s'exécute **une seule fois**.

```powershell
# Pré-configurer la subscription par défaut
Import-Module Az.Accounts
Update-AzConfig -DefaultSubscriptionForLogin "47b9d7c1-4229-4c02-b8b8-6d89a4a7ee38"

# Se connecter (ouvre https://login.microsoft.com/device)
Connect-AzAccount -TenantId "90b590b6-5ccc-471c-a0b0-8ee1389e07c7" -UseDeviceAuthentication

# Lancer le script de setup
.\scripts\setup_credentials.ps1
```

Après cette étape, `AZURE_CLIENT_SECRET` est dans le registre Windows (HKLM ou HKCU). **Plus aucune connexion Azure interactive ne sera nécessaire.**

### Vérification

```powershell
$len = [System.Environment]::GetEnvironmentVariable("AZURE_CLIENT_SECRET", "Machine")?.Length
if (-not $len) { $len = [System.Environment]::GetEnvironmentVariable("AZURE_CLIENT_SECRET", "User")?.Length }
Write-Host "AZURE_CLIENT_SECRET : $len car. dans le registre"
```

---

## Étape 6 — Créer la base de données

```powershell
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
pwd = get_secret('SQL-SACredential')
import subprocess
subprocess.run(['sqlcmd','-S','localhost\MSSQLSERVER2022','-U','sa','-P',pwd,'-i','sql\create_database.sql','-b'], check=True)
subprocess.run(['sqlcmd','-S','localhost\MSSQLSERVER2022','-U','sa','-P',pwd,'-i','sql\create_enrichissements.sql','-b'], check=True)
print('Base créée.')
"
```

---

## Étape 7 — Tester la chaîne complète

```powershell
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
from src.db import read_sql

pwd = get_secret('SQL-SACredential')
print('Vault OK — ' + str(len(pwd)) + ' car.')

df = read_sql('SELECT COUNT(*) AS n FROM dim.Annee')
print('SQL Server OK — dim.Annee : ' + str(df[chr(110)].iloc[0]) + ' lignes')
"
```

Résultat attendu :
```
Vault OK — 32 car.
SQL Server OK — dim.Annee : 81 lignes
```

---

## Étape 8 — Télécharger les données

```powershell
.venv\Scripts\python.exe src\fetch_data.py
.venv\Scripts\python.exe src\clean_data.py
```

---

## Étape 9 — Lancer Jupyter

```powershell
.venv\Scripts\jupyter.exe notebook --ip=0.0.0.0 --port=8888 --no-browser
```

Accès : `http://WWDBA01-D01.groupesifa.com:8888`

---

## Récapitulatif — commandes de démarrage

```powershell
# Démarrage normal (aucune authentification Azure requise)
cd d:\DEV\retraites-opendata
.venv\Scripts\jupyter.exe notebook --ip=0.0.0.0 --port=8888 --no-browser
```

C'est tout. Le SP s'authentifie automatiquement via le registre Windows.
