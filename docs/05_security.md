# Sécurité

## 1. Principes

1. **Aucun secret dans aucun fichier** — ni `.env`, ni code source, ni notebooks, ni logs
2. **Azure Key Vault comme source unique de vérité** pour tous les secrets applicatifs
3. **`AZURE_CLIENT_SECRET` dans le registre Windows** — chiffré par l'OS, hors de tout fichier texte
4. **Moindre privilège** — le SP n'a que `Get` et `List` sur les secrets du vault
5. **Auditabilité** — tous les accès Key Vault sont journalisés dans Azure Monitor

---

## 2. Architecture de gestion des secrets

```
┌─────────────────────────────────────────────────────────────────┐
│                     .env  (non secret)                          │
│  AZURE_KEYVAULT_URL = https://sifa-vault1.vault.azure.net/      │
│  AZURE_TENANT_ID   = 90b590b6-...  (identifiant public)        │
│  AZURE_CLIENT_ID   = 2ae721a6-...  (identifiant public)        │
│  SQL_SERVER / SQL_DATABASE / SQL_USER / ...  (config)          │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│          Registre Windows — HKLM (chiffré par l'OS)            │
│  AZURE_CLIENT_SECRET = ********  (40 car.)                      │
│  → Écrit UNE SEULE FOIS par scripts/setup_credentials.ps1      │
│  → Lu directement par src/vault.py via winreg                  │
│  → Jamais dans un fichier, jamais affiché                       │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│              Azure Key Vault — sifa-vault1                      │
│  SQL-SACredential        → mot de passe SQL Server sa          │
│  TenantID                → (utilisé par setup_credentials.ps1) │
│  datasvc-clientid        → (utilisé par setup_credentials.ps1) │
│  datasvc-secret-01       → (utilisé par setup_credentials.ps1) │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Flux d'authentification (runtime)

```
src/vault.py
    │
    ├── AZURE_TENANT_ID   ← os.getenv()  (chargé depuis .env)
    ├── AZURE_CLIENT_ID   ← os.getenv()  (chargé depuis .env)
    └── AZURE_CLIENT_SECRET ← os.getenv() ou winreg (HKLM/HKCU)
            │
            ▼
    ClientSecretCredential (azure-identity)
            │
            ▼
    SecretClient → sifa-vault1.vault.azure.net
            │
            ▼
    get_secret("SQL-SACredential") → mot de passe SQL
            │
            ▼
    src/db.py → SQLAlchemy → SQL Server MSSQLSERVER2022
```

---

## 4. Azure Key Vault — configuration

| Attribut | Valeur |
|---|---|
| Nom | `sifa-vault1` |
| URL | `https://sifa-vault1.vault.azure.net/` |
| Localisation | France Central |
| Modèle d'accès | **Access Policies** (pas Azure RBAC) |
| Accès réseau | Allow public access from all networks |

### Service Principal `sp-sifa-datasvc`

| Attribut | Valeur |
|---|---|
| Application (Client) ID | `2ae721a6-4ae1-45b3-8bb3-dba87845a23f` |
| Object ID (Enterprise App) | `0b8134b9-8d53-4f89-9d2a-0da12ca6fdb9` |
| Tenant | `90b590b6-5ccc-471c-a0b0-8ee1389e07c7` |
| Secrets dans vault | `TenantID`, `datasvc-clientid`, `datasvc-secret-01` |

### Access Policy assignée

| Permission | Valeur |
|---|---|
| Secrets — Get | ✓ |
| Secrets — List | ✓ |
| Clés, Certificats | ✗ (non accordés) |

> **Important :** Le vault est en mode **Access Policies**, pas Azure RBAC.
> Les role assignments IAM (Key Vault Secrets User) n'ont aucun effet sur le data plane dans ce mode.
> Seules les Access Policies contrôlent l'accès aux secrets.

---

## 5. `src/vault.py` — lecture du registre Windows

`AZURE_CLIENT_SECRET` est résolu dans l'ordre suivant :

1. Variable d'environnement du **processus** (`os.getenv`) — présente si injectée par le shell parent
2. Registre **HKLM** (`SYSTEM\CurrentControlSet\Control\Session Manager\Environment`)
3. Registre **HKCU** (`Environment`)
4. `EnvironmentError` si introuvable partout

Cela garantit que même les processus démarrés avant l'écriture dans le registre peuvent accéder au secret (cas des services Windows démarrés au boot).

---

## 6. Setup initial — `scripts/setup_credentials.ps1`

Ce script s'exécute **une seule fois** lors de l'installation du projet sur un nouveau serveur :

1. Authentification interactive Azure (`Connect-AzAccount`)
2. Lecture des 3 credentials depuis le vault (`TenantID`, `datasvc-clientid`, `datasvc-secret-01`)
3. Écriture de `AZURE_CLIENT_SECRET` dans le registre Windows (HKLM si admin, HKCU sinon)
4. `TENANT_ID` et `CLIENT_ID` sont écrits dans `.env` (ce sont des identifiants publics)

Après ce setup, **plus aucune session Azure interactive n'est nécessaire** pour faire tourner le projet.

---

## 7. Ce qui ne doit JAMAIS figurer dans le dépôt Git

- `.env` (listé dans `.gitignore`)
- Tout fichier `*.key`, `*.pem`, `*.pfx`
- Notebooks avec output contenant des valeurs de secrets
- Fichiers Parquet de `data/`

Vérification avant commit :
```powershell
git diff --staged | Select-String -Pattern "(password|secret|pwd|credential)" -CaseSensitive:$false
```

---

## 8. Classification des données

| Donnée | Sensibilité | Stockage |
|---|---|---|
| `AZURE_CLIENT_SECRET` | **Confidentiel** | Registre Windows (HKLM) |
| `SQL-SACredential` | **Confidentiel** | Key Vault uniquement |
| `AZURE_CLIENT_ID` / `AZURE_TENANT_ID` | **Interne** | `.env` (identifiants publics) |
| Données CNAV/INSEE/COR/DREES | **Publique** | Parquet + SQL Server |

---

## 9. Checklist sécurité avant mise en production

- [x] `AZURE_CLIENT_SECRET` dans le registre Windows — absent du `.env`
- [x] Access Policy `Get + List` secrets assignée à `sp-sifa-datasvc`
- [x] `pip-system-certs` installé (proxy SSL corporate)
- [ ] Créer un compte SQL dédié `retraites_app` (remplacer `sa`)
- [ ] Activer les alertes Azure Monitor sur les accès Key Vault anormaux
- [ ] Définir un mot de passe Jupyter : `jupyter notebook password`
- [ ] Restreindre le port 8888 au réseau interne uniquement
- [ ] Rotation du secret SP avant expiration (2 ans — à planifier)
