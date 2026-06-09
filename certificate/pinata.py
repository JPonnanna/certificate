import requests
import os
key = " "
secret = " "

def upload_to_pinata(filepath, api_key=key, api_secret=secret):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret
    }

    filename = os.path.basename(filepath)

    try:
        with open(filepath, 'rb') as f:
            files = {'file': (filename, f)}
            response = requests.post(url, files=files, headers=headers)

        if response.ok:
            cid = response.json()['IpfsHash']
            link = "https://cyan-magnificent-moose-511.mypinata.cloud/ipfs/" + cid
            print(response.json())
            print('✅ Upload complete')
            return link
        else:
            print("❌ Pinata upload failed:", response.status_code, response.text)
            return None
    except Exception as e:
        print("❌ Error uploading to Pinata:", str(e))
        return None
