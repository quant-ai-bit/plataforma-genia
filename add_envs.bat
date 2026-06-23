@echo off
echo Iniciando configuracion en Vercel...

echo 1. DATABASE_URL
call npx vercel env rm DATABASE_URL --yes --scope alejos-projects-14de84b4
call npx vercel env add DATABASE_URL production --value "postgresql://postgres.ppzsnsovdmxwofmuppfv:YOUR_SUPABASE_PASSWORD@aws-1-us-west-2.pooler.supabase.com:6543/postgres" --yes --scope alejos-projects-14de84b4

echo 2. SUPABASE_JWT_SECRET
call npx vercel env rm SUPABASE_JWT_SECRET --yes --scope alejos-projects-14de84b4
call npx vercel env add SUPABASE_JWT_SECRET production --value "YOUR_SUPABASE_JWT_SECRET" --yes --scope alejos-projects-14de84b4

echo 3. SUPABASE_URL
call npx vercel env rm SUPABASE_URL --yes --scope alejos-projects-14de84b4
call npx vercel env add SUPABASE_URL production --value "https://ppzsnsovdmxwofmuppfv.supabase.co" --yes --scope alejos-projects-14de84b4

echo 4. SUPABASE_SERVICE_KEY
call npx vercel env rm SUPABASE_SERVICE_KEY --yes --scope alejos-projects-14de84b4
call npx vercel env add SUPABASE_SERVICE_KEY production --value "YOUR_SUPABASE_SERVICE_KEY" --yes --scope alejos-projects-14de84b4

echo 5. FRONTEND_URL
call npx vercel env rm FRONTEND_URL --yes --scope alejos-projects-14de84b4
call npx vercel env add FRONTEND_URL production --value "https://plataforma-genia.vercel.app" --yes --scope alejos-projects-14de84b4

echo 6. NEXT_PUBLIC_API_URL
call npx vercel env rm NEXT_PUBLIC_API_URL --yes --scope alejos-projects-14de84b4
call npx vercel env add NEXT_PUBLIC_API_URL production --value "https://plataforma-genia.vercel.app" --yes --scope alejos-projects-14de84b4

echo 7. NEXT_PUBLIC_SUPABASE_URL
call npx vercel env rm NEXT_PUBLIC_SUPABASE_URL --yes --scope alejos-projects-14de84b4
call npx vercel env add NEXT_PUBLIC_SUPABASE_URL production --value "https://ppzsnsovdmxwofmuppfv.supabase.co" --yes --scope alejos-projects-14de84b4

echo 8. NEXT_PUBLIC_SUPABASE_ANON_KEY
call npx vercel env rm NEXT_PUBLIC_SUPABASE_ANON_KEY --yes --scope alejos-projects-14de84b4
call npx vercel env add NEXT_PUBLIC_SUPABASE_ANON_KEY production --value "YOUR_SUPABASE_ANON_KEY" --yes --scope alejos-projects-14de84b4

echo 9. GROQ_API_KEY
call npx vercel env rm GROQ_API_KEY --yes --scope alejos-projects-14de84b4
call npx vercel env add GROQ_API_KEY production --value "YOUR_GROQ_API_KEY" --yes --scope alejos-projects-14de84b4

echo 10. GEMINI_API_KEY
call npx vercel env rm GEMINI_API_KEY --yes --scope alejos-projects-14de84b4
call npx vercel env add GEMINI_API_KEY production --value "YOUR_GEMINI_API_KEY" --yes --scope alejos-projects-14de84b4

echo 11. OPENROUTER_API_KEY
call npx vercel env rm OPENROUTER_API_KEY --yes --scope alejos-projects-14de84b4
call npx vercel env add OPENROUTER_API_KEY production --value "YOUR_OPENROUTER_API_KEY" --yes --scope alejos-projects-14de84b4

echo Proceso completado con exito.
