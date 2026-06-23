$envs = [ordered]@{
    "ENVIRONMENT" = "production"
    "DATABASE_URL" = "postgresql://postgres.ppzsnsovdmxwofmuppfv:YOUR_SUPABASE_PASSWORD@aws-1-us-west-2.pooler.supabase.com:6543/postgres"
    "SUPABASE_JWT_SECRET" = "YOUR_SUPABASE_JWT_SECRET"
    "SUPABASE_URL" = "https://ppzsnsovdmxwofmuppfv.supabase.co"
    "SUPABASE_SERVICE_KEY" = "YOUR_SUPABASE_SERVICE_KEY"
    "FRONTEND_URL" = "https://plataforma-genia.vercel.app"
    "NEXT_PUBLIC_API_URL" = "https://plataforma-genia.vercel.app"
    "NEXT_PUBLIC_SUPABASE_URL" = "https://ppzsnsovdmxwofmuppfv.supabase.co"
    "NEXT_PUBLIC_SUPABASE_ANON_KEY" = "YOUR_SUPABASE_ANON_KEY"
    "GROQ_API_KEY" = "YOUR_GROQ_API_KEY"
    "GEMINI_API_KEY" = "YOUR_GEMINI_API_KEY"
    "OPENROUTER_API_KEY" = "YOUR_OPENROUTER_API_KEY"
}

$scope = "alejos-projects-14de84b4"

foreach ($key in $envs.Keys) {
    Write-Host "Configurando $key..."
    # Eliminar la variable si existe para evitar conflictos
    npx vercel env rm "$key" --yes --scope "$scope" *>$null
    # Agregar la variable con el nuevo valor
    npx vercel env add "$key" production --value "$($envs[$key])" --yes --scope "$scope"
}
Write-Host "Configuracion de variables completada exitosamente."
