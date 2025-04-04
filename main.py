import os
import requests
import random
import tweepy

# Environment variables (set these before running)
PROMPT = os.environ.get('PROMPT', '')
PROMPT_X = os.environ.get('PROMPT_X', '')
API_KEY = os.environ.get('GOOGLE_API_KEY', '')
CLIENT_ID = os.environ.get('LINKEDIN_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('LINKEDIN_CLIENT_SECRET', '')
ACCESS_TOKEN = os.environ.get('LINKEDIN_ACCESS_TOKEN', '')
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"
bearer_token = os.environ.get('X_BEARER_TOKEN', '')
consumer_key = os.environ.get('X_API_KEY', '')
consumer_secret = os.environ.get('X_API_SECRET', '')
access_token_twitter = os.environ.get('X_ACCESS_TOKEN', '')
access_token_secret = os.environ.get('X_ACCESS_SECRET', '')

def get_ai_data(prompt):
    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "text": prompt
                    }
                ]
            }
        ]
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(url, json=payload, headers=headers)
    if response.status_code == 200:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    else:
        print(f"Error fetching AI data: {response.status_code}")
        return None

def get_linkedin_userinfo(access_token):
    # Use the OAuth2 userinfo endpoint which returns the "sub" (subject) field.
    info_url = "https://api.linkedin.com/v2/userinfo"
    headers = {'Authorization': f'Bearer {access_token}'}
    response = requests.get(info_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching user info: {response.status_code}")
        print(response.text)
        return None

def upload_image_to_linkedin(access_token, image_url, owner):
    register_url = "https://api.linkedin.com/v2/assets?action=registerUpload"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    image_register_payload = {
        "registerUploadRequest": {
            "recipes": ["urn:li:digitalmediaRecipe:feedshare-image"],
            "owner": owner,
            "serviceRelationships": [
                {
                    "relationshipType": "OWNER",
                    "identifier": "urn:li:userGeneratedContent"
                }
            ]
        }
    }
    reg_response = requests.post(register_url, headers=headers, json=image_register_payload)
    if reg_response.status_code != 200:
        print(f"Error registering image: {reg_response.status_code}")
        print(reg_response.text)
        return None
    reg_data = reg_response.json()
    upload_url = reg_data['value']['uploadMechanism']['com.linkedin.digitalmedia.uploading.MediaUploadHttpRequest']['uploadUrl']
    asset = reg_data['value']['asset']

    try:
        img_response = requests.get(image_url)
        img_response.raise_for_status()
        img_bytes = img_response.content
    except Exception as e:
        print("Error downloading image from GitHub:", e)
        return None

    upload_headers = {'Authorization': f'Bearer {access_token}'}
    upload_response = requests.put(upload_url, data=img_bytes, headers=upload_headers)
    if upload_response.status_code not in [200, 201]:
        print(f"Image upload failed: {upload_response.status_code}")
        print(upload_response.text)
        return None
    return asset

def post_to_linkedin(access_token, text_content):
    user_info = get_linkedin_userinfo(access_token)
    if not user_info or 'sub' not in user_info:
        print("Failed to retrieve LinkedIn user info.")
        return None

    member_id = user_info['sub']
    owner = f"urn:li:person:{member_id}"
    print("Posting as LinkedIn member ID:", member_id)

    # Pick a random image from GitHub (absolute URL)
    image_num = 1#random.randint(1, 20)
    github_image_url = f"https://raw.githubusercontent.com/artistkaransaini/autopost/void/art/art{image_num}.jpg"
    print("Using image URL:", github_image_url)

    asset_urn = upload_image_to_linkedin(access_token, github_image_url, owner)
    if not asset_urn:
        print("Image upload failed, attempting text-only post.")
        share_media_category = "NONE"
        media_payload = None
    else:
        share_media_category = "IMAGE"
        media_payload = [
            {
                "status": "READY",
                "description": {"text": "Auto-generated artwork from GitHub"},
                "media": asset_urn,
                "title": {"text": f"Artwork #{image_num}"}
            }
        ]

    post_url = "https://api.linkedin.com/v2/ugcPosts"
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json',
        'X-Restli-Protocol-Version': '2.0.0'
    }
    share_content = {
        "shareCommentary": {"text": text_content},
        "shareMediaCategory": share_media_category,
    }
    if media_payload:
        share_content["media"] = media_payload

    payload = {
        "author": owner,
        "lifecycleState": "PUBLISHED",
        "specificContent": {"com.linkedin.ugc.ShareContent": share_content},
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
    }

    response = requests.post(post_url, headers=headers, json=payload)
    print("LinkedIn post response status:", response.status_code)
    try:
        response_json = response.json()
        print("LinkedIn response JSON:", response_json)
    except Exception as e:
        print("Error parsing LinkedIn response:", e)
        response_json = None

    if response.status_code == 201:
        print("Successfully posted to LinkedIn!")
        return response_json
    else:
        print("Failed to post to LinkedIn.")
        return None

def post_tweet(text):
    client = tweepy.Client(
        bearer_token=bearer_token,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token_twitter,
        access_token_secret=access_token_secret
    )
    response = client.create_tweet(text=text)
    print("Tweet response:", response)
    return response

def should_post():
    # Approximately 50% chance for either platform.
    return random.randint(1, 2) == 1

def main():
    if should_post():
        print("Proceeding to post on LinkedIn...")
        text_content = get_ai_data(PROMPT)
        if text_content:
            result = post_to_linkedin(ACCESS_TOKEN, text_content)
            if result:
                print("LinkedIn post successful!")
            else:
                print("LinkedIn post failed.")
        else:
            print("Failed to get AI data for LinkedIn post.")
    else:
        print("Proceeding to post on Twitter...")
        tweet_text = get_ai_data(PROMPT_X)
        if tweet_text:
            result_tweet = post_tweet(tweet_text)
            print("Tweet posted successfully!")
        else:
            print("Failed to get AI data for tweet.")

if __name__ == "__main__":
    main()
