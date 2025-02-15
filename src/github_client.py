import os
import requests
import backoff
import time
from dotenv import load_dotenv
from typing import Dict, Optional, Any
import pandas as pd

load_dotenv(override=True)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=5
)
def get_github_user(username: str, token: str) -> Optional[Dict[str, Any]]:
    """
    Fetches GitHub user details using the GitHub API with rate limit handling.

    This function retries requests using exponential backoff if an API error occurs.

    Args:
        username (str): GitHub username to retrieve.
        token (str): Personal access token for GitHub API authentication.

    Returns:
        Optional[Dict[str, Any]]: Dictionary containing GitHub user details if found, including:
            - 'login' (str): GitHub username.
            - 'created_at' (str): GitHub account creation date (ISO 8601 format).
            - 'updated_at' (str): Last profile update date (ISO 8601 format).
            - 'public_repos' (int): Number of public repositories.
            Returns None if the user is not found or if the request fails.
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


def update_with_github(
    followers_df: pd.DataFrame, filter_connected_profiles: bool = True
) -> pd.DataFrame:
    """
    Updates the followers DataFrame with GitHub profile information.

    This function fetches GitHub user details for followers who have connected GitHub profiles.
    It adds account creation date, last update date, and the number of public repositories.

    By default, it only updates users where 'category' is 'Connected Profiles'.
    If `filter_connected_profiles` is False, it updates all users with a GitHub username.

    Args:
        followers_df (pd.DataFrame): DataFrame containing follower information, including GitHub usernames.
        filter_connected_profiles (bool, optional): If True (default), filters for users in the "Connected Profiles" category.
                                                    If False, fetches data for all users with GitHub usernames.

    Returns:
        pd.DataFrame: A new DataFrame with additional GitHub profile columns:
            - 'github_created_at' (str): GitHub account creation date.
            - 'github_updated_at' (str): Last GitHub profile update date.
            - 'github_public_repos' (int): Number of public repositories.
    """

    # Apply filter if enabled
    if filter_connected_profiles:
        github_users = followers_df[
            (followers_df["category"] == "Connected Profiles")
            & (followers_df["github_username"].notna())
        ].copy()
    else:
        github_users = followers_df[followers_df["github_username"].notna()].copy()

    # Initialize new columns
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

    return github_users
