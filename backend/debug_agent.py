import sqlite3
from services.encryption_service import decrypt
from config import settings

conn = sqlite3.connect('data/genia.db')
cursor = conn.cursor()
cursor.execute('SELECT id, name, whatsapp_access_token, whatsapp_app_secret FROM agents WHERE id = ?', ('547c07f714394e399c504d4bb3da37ac',))
row = cursor.fetchone()
conn.close()

print(f'ID: {row[0]}')
print(f'Name: {row[1]}')
print(f'Access Token (encrypted): {row[2][:80] if row[2] else None}...')
print(f'App Secret (encrypted): {row[3][:80] if row[3] else None}...')

print(f'ENCRYPTION_KEY set: {bool(settings.encryption_key)}')
print(f'ENCRYPTION_KEY (first 20 chars): {settings.encryption_key[:20] if settings.encryption_key else None}')

if row[2]:
    decrypted_token = decrypt(row[2])
    print(f'Decrypted Access Token (first 50 chars): {decrypted_token[:50] if decrypted_token else "FAILED"}')

if row[3]:
    decrypted_secret = decrypt(row[3])
    print(f'Decrypted App Secret (first 50 chars): {decrypted_secret[:50] if decrypted_secret else "FAILED"}')