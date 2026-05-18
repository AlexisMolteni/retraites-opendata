# ============================================================
# Amorçage des credentials SP — à exécuter UNE SEULE FOIS
# par un administrateur connecté à Azure (Connect-AzAccount).
#
# Ce script lit les 3 credentials depuis le vault
# et les injecte comme variables d'environnement MACHINE
# (registre Windows chiffré — jamais dans un fichier).
# ============================================================

#Requires -RunAsAdministrator

param(
    [string]$VaultName = "sifa-vault1"
)

Import-Module Az.Accounts, Az.KeyVault -ErrorAction Stop

# Vérifier la connexion Azure
if (-not (Get-AzContext -ErrorAction SilentlyContinue)) {
    Write-Error "Non connecté à Azure. Exécuter Connect-AzAccount d'abord."
    exit 1
}

Write-Host "Lecture des credentials depuis $VaultName..."

$tenantId  = Get-AzKeyVaultSecret -VaultName $VaultName -Name "TenantID"          -AsPlainText -ErrorAction Stop
$clientId  = Get-AzKeyVaultSecret -VaultName $VaultName -Name "datasvc-clientid"  -AsPlainText -ErrorAction Stop
$clientSec = Get-AzKeyVaultSecret -VaultName $VaultName -Name "datasvc-secret-01" -AsPlainText -ErrorAction Stop

# Injecter en variables d'environnement MACHINE (pas Process, pas User)
[System.Environment]::SetEnvironmentVariable("AZURE_TENANT_ID",     $tenantId,  [System.EnvironmentVariableTarget]::Machine)
[System.Environment]::SetEnvironmentVariable("AZURE_CLIENT_ID",     $clientId,  [System.EnvironmentVariableTarget]::Machine)
[System.Environment]::SetEnvironmentVariable("AZURE_CLIENT_SECRET", $clientSec, [System.EnvironmentVariableTarget]::Machine)

Write-Host "Variables d'environnement système configurées :"
Write-Host "  AZURE_TENANT_ID     = $($tenantId.Substring(0,8))... ($($tenantId.Length) car.)"
Write-Host "  AZURE_CLIENT_ID     = $($clientId.Substring(0,8))... ($($clientId.Length) car.)"
Write-Host "  AZURE_CLIENT_SECRET = *** ($($clientSec.Length) car.) — non affiché"
Write-Host ""
Write-Host "Les valeurs sont stockées dans le registre Windows (HKLM)."
Write-Host "Aucun fichier texte ne contient ces secrets."
Write-Host "Un redémarrage des services / nouvelles sessions est nécessaire pour les prendre en compte."
