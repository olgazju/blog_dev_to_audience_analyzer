import os
import requests
import backoff
from time import time
from dotenv import load_dotenv
from typing import Dict, Optional
import pandas as pd

load_dotenv(override=True)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=5
)
def get_github_user(username: str, token: str) -> Optional[Dict]:
    """
    Fetch GitHub user details using GitHub API, with rate limit handling.

    Args:
        username: GitHub username to retrieve
        token: Personal access token for GitHub API authentication

    Returns:
        Dictionary containing user details if found, None otherwise
    """
    url = f"https://api.github.com/users/{username}"
    headers = {"Authorization": f"token {token}"}

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            print(response.json())
            return response.json()
        elif response.status_code == 404:
            print(f"User {username} not found.")
            return None
        elif response.status_code == 429:
            print("Rate limit exceeded. Waiting before retrying...")
            time.sleep(60)
        else:
            print(f"Failed to fetch {username}. Status code: {response.status_code}")
            return None


def update_with_github(followers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Updates followers DataFrame with GitHub profile information.

    Fetches GitHub data for followers who have connected GitHub profiles and adds
    their account creation date, last update date, and public repository count.

    Args:
        followers_df: DataFrame containing follower information including GitHub usernames

    Returns:
        pd.DataFrame: Updated DataFrame with additional GitHub profile columns
    """
    github_users = followers_df[
        (followers_df["category"] == "Connected Profiles")
        & (followers_df["github_username"].notna())
    ].copy()

    github_users["github_created_at"] = None
    github_users["github_updated_at"] = None
    github_users["github_public_repos"] = None

    for index, row in github_users.iterrows():
        username = row["github_username"]
        user_data = get_github_user(username, GITHUB_TOKEN)

        if user_data:
            github_users.at[index, "github_created_at"] = user_data.get("created_at")
            github_users.at[index, "github_updated_at"] = user_data.get("updated_at")
            github_users.at[index, "github_public_repos"] = user_data.get(
                "public_repos"
            )
