# ============================================================
# Création du Service Principal pour retraites-opendata
# À exécuter par un Azure AD Application Administrator
# depuis une session sans Conditional Access (réseau interne)
# ============================================================

param(
    [string]$TenantId      = "90b590b6-5ccc-471c-a0b0-8ee1389e07c7",
    [string]$VaultName     = "sifa-vault1",
    [string]$SecretName    = "SQL-SACredential",
    [string]$AppName       = "sp-retraites-opendata"
)

Import-Module Az.Accounts, Az.KeyVault, Az.Resources -ErrorAction Stop

# 1. Connexion
Connect-AzAccount -TenantId $TenantId -UseDeviceAuthentication

# 2. Créer le Service Principal avec un secret auto-généré (validité 2 ans)
Write-Host "`nCréation du Service Principal '$AppName'..."
$endDate = (Get-Date).AddYears(2)
$sp = New-AzADServicePrincipal -DisplayName $AppName -EndDate $endDate
$spSecret = ($sp.PasswordCredentials | Select-Object -First 1).SecretText

Write-Host "AppId    : $($sp.AppId)"
Write-Host "ObjectId : $($sp.Id)"

# 3. Assigner "Key Vault Secrets User" sur le vault
#    (RBAC — nécessite que le vault soit en mode Azure RBAC)
Write-Host "`nAssignation du rôle 'Key Vault Secrets User'..."
$vault = Get-AzKeyVault -VaultName $VaultName
if ($vault.EnableRbacAuthorization) {
    New-AzRoleAssignment `
        -ObjectId $sp.Id `
        -RoleDefinitionName "Key Vault Secrets User" `
        -Scope $vault.ResourceId `
        -ErrorAction Stop
    Write-Host "Rôle RBAC assigné."
} else {
    # Mode access policy
    Set-AzKeyVaultAccessPolicy `
        -VaultName $VaultName `
        -ObjectId $sp.Id `
        -PermissionsToSecrets get,list `
        -ErrorAction Stop
    Write-Host "Access Policy assignée."
}

# 4. Afficher les variables à mettre dans .env / Key Vault
Write-Host "`n=== Variables à ajouter dans .env ==="
Write-Host "AZURE_TENANT_ID=$TenantId"
Write-Host "AZURE_CLIENT_ID=$($sp.AppId)"
Write-Host "AZURE_CLIENT_SECRET=$spSecret"
Write-Host "`nConservez le AZURE_CLIENT_SECRET en lieu sûr — il n'est pas récupérable."
Write-Host "Recommandé : le stocker dans Key Vault sous le nom 'SP-RetraitesOpenData-Secret'"

# 5. Optionnel — stocker le secret SP dans le vault
$storeInVault = Read-Host "`nStocker AZURE_CLIENT_SECRET dans Key Vault ? (o/n)"
if ($storeInVault -eq 'o') {
    Set-AzKeyVaultSecret -VaultName $VaultName `
                         -Name "SP-RetraitesOpenData-Secret" `
                         -SecretValue (ConvertTo-SecureString $spSecret -AsPlainText -Force)
    Write-Host "Secret stocké dans Key Vault sous 'SP-RetraitesOpenData-Secret'."
}
