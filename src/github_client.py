import os
import requests
import backoff
from time import time
from dotenv import load_dotenv


# Load environment variables from .env file
load_dotenv(override=True)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


# Function to fetch GitHub user details with rate limit handling
@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=5
)
def get_github_user(username, token):
    """
    Fetch GitHub user details using GitHub API, with rate limit handling.

    Parameters:
    - username (str): GitHub username to retrieve.
    - token (str): Personal access token for GitHub API authentication.
    - retries (int): Number of retries for rate-limited requests.

    Returns:
    - dict: User details if found, otherwise None.
    """
    url = f"https://api.github.com/users/{username}"
    headers = {"Authorization": f"token {token}"}

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print(response.json())
            return response.json()  # Returns user details as a dictionary
        elif response.status_code == 404:
            print(f"User {username} not found.")
            return None
        elif response.status_code == 429:
            print("Rate limit exceeded. Waiting before retrying...")
            time.sleep(60)  # Wait 60 seconds before retrying (adjust as needed)
        else:
            print(f"Failed to fetch {username}. Status code: {response.status_code}")
            return None


def update_with_github(followers_df):
    github_users = followers_df[
        (followers_df["category"] == "Connected Profiles")
        & (followers_df["github_username"].notna())
    ].copy()

    # Assuming `github_users` DataFrame has a column `github_username`
    # Initialize columns for GitHub info
    github_users["github_created_at"] = None
    github_users["github_updated_at"] = None
    github_users["github_public_repos"] = None

    # Iterate over each username and update the DataFrame with GitHub data
    for index, row in github_users.iterrows():
        username = row["github_username"]
        user_data = get_github_user(username, GITHUB_TOKEN)

        if user_data:
            github_users.at[index, "github_created_at"] = user_data.get("created_at")
            github_users.at[index, "github_updated_at"] = user_data.get("updated_at")
            github_users.at[index, "github_public_repos"] = user_data.get(
                "public_repos"
            )
