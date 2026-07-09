# Script para actualizar las variables de entorno de producción en Vercel para PLATAFORMA GENIA

# Cargar variables desde .env.production local y seguro
$envFile = ".env.production"
if (-not (Test-Path $envFile)) {
    $envFile = "../.env.production"
}
if (-not (Test-Path $envFile)) {
    Write-Error "No se pudo encontrar el archivo .env.production."
    exit 1
}

Write-Host "Cargando variables desde: $(Resolve-Path $envFile)"
$envs = [ordered]@{}
Get-Content $envFile | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line -match "^([^=]+)=(.*)$") {
        $key = $Matches[1].Trim()
        $value = $Matches[2].Trim()
        # Limpiar comillas si existen
        if ($value -match "^`\"(.*)`\"$") { $value = $Matches[1] }
        elseif ($value -match "^'(.*)'$") { $value = $Matches[1] }
        $envs[$key] = $value
    }
}

if (-not $envs.Contains("ENVIRONMENT")) {
    $envs["ENVIRONMENT"] = "production"
}

$scope = "alejos-projects-14de84b4"

foreach ($key in $envs.Keys) {
    Write-Host "Configurando variable $key en Vercel..."
    # Eliminar la variable si existe para evitar duplicados
    vercel env rm "$key" production --yes --scope "$scope" *>$null
    # Agregar la variable con el nuevo valor en producción
    vercel env add "$key" production --value "$($envs[$key])" --yes --scope "$scope"
}

Write-Host "Configuración de variables de producción en Vercel finalizada con éxito."
