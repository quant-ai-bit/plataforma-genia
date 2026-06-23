Write-Host "Iniciando configuracion plana de variables en Vercel..."

Write-Host "1. DATABASE_URL"
npx vercel env rm DATABASE_URL --yes --scope alejos-projects-14de84b4
npx vercel env add DATABASE_URL production --value "postgresql://postgres.ppzsnsovdmxwofmuppfv:YOUR_SUPABASE_PASSWORD@aws-1-us-west-2.pooler.supabase.com:6543/postgres" --yes --scope alejos-projects-14de84b4

Write-Host "2. SUPABASE_JWT_SECRET"
npx vercel env rm SUPABASE_JWT_SECRET --yes --scope alejos-projects-14de84b4
npx vercel env add SUPABASE_JWT_SECRET production --value "YOUR_SUPABASE_JWT_SECRET" --yes --scope alejos-projects-14de84b4

Write-Host "3. SUPABASE_URL"
npx vercel env rm SUPABASE_URL --yes --scope alejos-projects-14de84b4
npx vercel env add SUPABASE_URL production --value "https://ppzsnsovdmxwofmuppfv.supabase.co" --yes --scope alejos-projects-14de84b4

Write-Host "4. SUPABASE_SERVICE_KEY"
npx vercel env rm SUPABASE_SERVICE_KEY --yes --scope alejos-projects-14de84b4
npx vercel env add SUPABASE_SERVICE_KEY production --value "YOUR_SUPABASE_SERVICE_KEY" --yes --scope alejos-projects-14de84b4

Write-Host "5. FRONTEND_URL"
npx vercel env rm FRONTEND_URL --yes --scope alejos-projects-14de84b4
npx vercel env add FRONTEND_URL production --value "https://plataforma-genia.vercel.app" --yes --scope alejos-projects-14de84b4

Write-Host "6. NEXT_PUBLIC_API_URL"
npx vercel env rm NEXT_PUBLIC_API_URL --yes --scope alejos-projects-14de84b4
npx vercel env add NEXT_PUBLIC_API_URL production --value "https://plataforma-genia.vercel.app" --yes --scope alejos-projects-14de84b4

Write-Host "7. NEXT_PUBLIC_SUPABASE_URL"
npx vercel env rm NEXT_PUBLIC_SUPABASE_URL --yes --scope alejos-projects-14de84b4
npx vercel env add NEXT_PUBLIC_SUPABASE_URL production --value "https://ppzsnsovdmxwofmuppfv.supabase.co" --yes --scope alejos-projects-14de84b4

Write-Host "8. NEXT_PUBLIC_SUPABASE_ANON_KEY"
npx vercel env rm NEXT_PUBLIC_SUPABASE_ANON_KEY --yes --scope alejos-projects-14de84b4
npx vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --value "YOUR_SUPABASE_ANON_KEY" --yes --scope alejos-projects-14de84b4

Write-Host "9. GROQ_API_KEY"
npx vercel env rm GROQ_API_KEY --yes --scope alejos-projects-14de84b4
npx vercel env add GROQ_API_KEY production --value "YOUR_GROQ_API_KEY" --yes --scope alejos-projects-14de84b4

Write-Host "10. GEMINI_API_KEY"
npx vercel env rm GEMINI_API_KEY --yes --scope alejos-projects-14de84b4
npx vercel env add GEMINI_API_KEY production --value "YOUR_GEMINI_API_KEY" --yes --scope alejos-projects-14de84b4

Write-Host "11. OPENROUTER_API_KEY"
npx vercel env rm OPENROUTER_API_KEY --yes --scope alejos-projects-14de84b4
npx vercel env add OPENROUTER_API_KEY production --value "YOUR_OPENROUTER_API_KEY" --yes --scope alejos-projects-14de84b4

Write-Host "Proceso completado."
