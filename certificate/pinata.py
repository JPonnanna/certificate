import requests
import os
key = "c70644a9c2e5791d7fa4"
secret = "e4d7190407797043e001aea7c192934b0dd8867aba912cf56d2b043e09a05fcc"

def upload_to_pinata(filepath, api_key=key, api_secret=secret):
    url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
    headers = {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": api_secret
    }

    # Just send the base filename, not full path, to Pinata
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

# def upload_to_pinata(filepath, api_key=key, api_secret=secret):
#     url = "https://api.pinata.cloud/pinning/pinFileToIPFS"
#     headers = {
#         "pinata_api_key": api_key,
#         "pinata_secret_api_key": api_secret
#     }

#     with open(filepath, 'rb') as f:
#         files = {'file': (filepath, f)}
#         response = requests.post(url, files=files, headers=headers)

#     if response.ok:
#         cid = response.json()['IpfsHash']
#         link="https://cyan-magnificent-moose-511.mypinata.cloud/ipfs/" + cid
#         print('upload complete')
#         return link
#     else:
#         print("❌ Pinata upload failed:", response.status_code, response.text)
#         return None

# # ✅ Replace these with your Pinata credentials


# # ✅ Replace with the path to your file
# # cid = upload_to_pinata("Tiger.pdf", api_key, api_secret)

# # if cid:
# #     print("✅ IPFS CID:", cid)
# #     print("🔗 View file at: https://ipfs.io/ipfs/" + cid)

