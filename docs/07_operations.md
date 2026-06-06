# Guide Opérationnel

## 1. Démarrage normal (session quotidienne)

```powershell
cd d:\DEV\retraites-opendata
.venv\Scripts\jupyter.exe notebook --ip=0.0.0.0 --port=8888 --no-browser
```

**Aucune authentification Azure requise.** Le SP lit `AZURE_CLIENT_SECRET` directement dans le registre Windows à chaque démarrage.

---

## 2. Vérifier que tout fonctionne

```powershell
cd d:\DEV\retraites-opendata
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
from src.db import read_sql
print('Vault : ' + str(len(get_secret('SQL-SACredential'))) + ' car. OK')
df = read_sql('SELECT COUNT(*) AS n FROM dim.Annee')
print('SQL : ' + str(df['n'].iloc[0]) + ' lignes OK')
"
```

---

## 3. Rafraîchissement des données

### 3.1 Données CNAV (annuel — T2/T3)

```powershell
cd d:\DEV\retraites-opendata
.venv\Scripts\python.exe src\fetch_data.py
.venv\Scripts\python.exe src\clean_data.py
```

### 3.2 Données INSEE (annuel ou trimestriel)

```powershell
.venv\Scripts\python.exe src\fetch_external.py [TOKEN_INSEE]
```

Pour la pyramide des âges et l'espérance de vie (Excel manuel) :
1. Télécharger depuis https://www.insee.fr/fr/statistiques/1893198
2. Placer dans `data\raw\external\`
3. Lancer via notebook `02_descriptive_stats.ipynb`

### 3.3 Données COR et DREES (annuel)

Télécharger les fichiers Excel depuis leurs portails respectifs, placer dans `data\raw\external\`, utiliser les fonctions `load_cor_projections()` et `load_drees_pensions()` de `src\fetch_external.py`.

---

## 4. Opérations SQL Server

### Se connecter à la base

```powershell
cd d:\DEV\retraites-opendata
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
import subprocess
pwd = get_secret('SQL-SACredential')
subprocess.run(['sqlcmd','-S','localhost\MSSQLSERVER2022','-U','sa','-P',pwd,'-d','RetraitesOpenData'])
"
```

### Recréer la base depuis zéro

```powershell
.venv\Scripts\python.exe -c "
import sys, subprocess; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
pwd = get_secret('SQL-SACredential')
srv = 'localhost\MSSQLSERVER2022'
subprocess.run(['sqlcmd','-S',srv,'-U','sa','-P',pwd,'-i','sql\create_database.sql','-b'], check=True)
subprocess.run(['sqlcmd','-S',srv,'-U','sa','-P',pwd,'-i','sql\create_enrichissements.sql','-b'], check=True)
print('Base recrée.')
"
```

### Vérifier l'état des tables

```sql
SELECT s.name AS schema_name, t.name AS table_name, p.rows AS nb_lignes
FROM sys.tables t
JOIN sys.schemas s ON s.schema_id = t.schema_id
JOIN sys.partitions p ON p.object_id = t.object_id AND p.index_id IN (0,1)
ORDER BY s.name, p.rows DESC;
```

---

## 5. Gestion de Jupyter

### Vérifier que Jupyter tourne

```powershell
netstat -an | findstr ":8888"
```

### Arrêter Jupyter

```powershell
.venv\Scripts\jupyter.exe notebook stop 8888
```

### Définir un mot de passe permanent

```powershell
.venv\Scripts\jupyter.exe notebook password
```

---

## 6. Renouvellement de `AZURE_CLIENT_SECRET`

Le secret SP expire après **2 ans**. Avant expiration, un administrateur Azure AD doit :

1. Renouveler le secret dans Azure Portal → App registrations → `sp-sifa-datasvc` → Certificates & secrets
2. Mettre à jour le secret dans Key Vault :
   ```powershell
   Connect-AzAccount -TenantId "90b590b6-5ccc-471c-a0b0-8ee1389e07c7" -UseDeviceAuthentication
   Set-AzKeyVaultSecret -VaultName "sifa-vault1" -Name "datasvc-secret-01" `
       -SecretValue (ConvertTo-SecureString "<nouveau-secret>" -AsPlainText -Force)
   ```
3. Relancer le script de setup sur le serveur :
   ```powershell
   .\scripts\setup_credentials.ps1
   ```

---

## 7. Sauvegarde

| Élément | Fréquence | Méthode |
|---|---|---|
| `data\raw\*.parquet` | Après chaque `fetch_data.py` | Copie vers NAS ou Azure Blob |
| Base SQL `RetraitesOpenData` | Hebdomadaire | SQL Server Backup (voir ci-dessous) |
| `reports\` | Après chaque analyse | Copie vers SharePoint/Teams |

### Sauvegarde SQL Server

```powershell
.venv\Scripts\python.exe -c "
import sys, subprocess; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
from datetime import datetime
pwd = get_secret('SQL-SACredential')
date = datetime.now().strftime('%Y%m%d')
subprocess.run(['sqlcmd','-S','localhost\MSSQLSERVER2022','-U','sa','-P',pwd,'-Q',
    f'BACKUP DATABASE RetraitesOpenData TO DISK = ' +
    chr(39) + f'D:\Backups\RetraitesOpenData_{date}.bak' + chr(39) +
    ' WITH FORMAT, COMPRESSION, STATS = 10'], check=True)
"
```

---

## 8. Troubleshooting

### `EnvironmentError: Credentials SP manquants : AZURE_CLIENT_SECRET`

Le secret n'est pas dans le registre. Relancer le script de setup :
```powershell
Connect-AzAccount -TenantId "90b590b6-5ccc-471c-a0b0-8ee1389e07c7" -UseDeviceAuthentication
.\scripts\setup_credentials.ps1
```

### `Forbidden` sur le vault

Vérifier dans le portail Azure → Key Vault `sifa-vault1` :
1. **Access configuration** → Permission model = **Vault access policy** (pas Azure RBAC)
2. **Access policies** → `sp-sifa-datasvc` doit avoir **Get + List** sur les secrets
3. **Networking** → "Allow public access from all networks" ✓

### `pyodbc.OperationalError: Login failed`

```powershell
# Vérifier que le service SQL tourne
Get-Service | Where-Object Name -like "*MSSQLSERVER2022*"
# Tester avec le secret récupéré depuis le vault
.venv\Scripts\python.exe -c "
import sys; sys.path.insert(0, '.')
from dotenv import load_dotenv; load_dotenv()
from src.vault import get_secret
import subprocess
subprocess.run(['sqlcmd','-S','localhost\MSSQLSERVER2022','-U','sa','-P',get_secret('SQL-SACredential'),'-Q','SELECT 1'])
"
```

### `SSL: CERTIFICATE_VERIFY_FAILED`

`pip-system-certs` doit être installé :
```powershell
.venv\Scripts\python.exe -m pip install pip-system-certs
```

### `No module named 'dotenv'` ou autre module

L'environnement virtuel n'est pas utilisé. Utiliser explicitement `.venv\Scripts\python.exe`.
