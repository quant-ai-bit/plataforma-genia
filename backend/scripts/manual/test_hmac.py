import hmac
import hashlib
import json

from services.whatsapp_service import verify_whatsapp_signature

# Test with a known payload and signature
test_payload = json.dumps({
    "object": "page",
    "entry": [{
        "id": "1223534394168307",
        "changes": [{
            "value": {
                "messages": [{
                    "from": "57300123456",
                    "id": "test-id",
                    "type": "text",
                    "text": {"body": "hola"}
                }],
                "metadata": {"phone_number_id": "1223534394168307"}
            }
        }]
    }]
}).encode('utf-8')

# This is the app_secret from the database
test_secret = 'f459097da57e8d4d98463f9fe09545ca'

# Calculate expected signature
expected_sig = hmac.new(test_secret.encode('utf-8'), test_payload, hashlib.sha256).hexdigest()
print(f'Expected signature: {expected_sig}')

# Test verification
result = verify_whatsapp_signature(test_payload, f'sha256={expected_sig}', test_secret)
print(f'Verification result: {result}')

# Now test with a different secret (simulating wrong secret)
wrong_secret = 'wrong_secret'
result2 = verify_whatsapp_signature(test_payload, f'sha256={expected_sig}', wrong_secret)
print(f'Verification with wrong secret: {result2}')