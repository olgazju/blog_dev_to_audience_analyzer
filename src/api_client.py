import os
import requests
import pandas as pd
import backoff
from time import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
API_KEY = os.getenv("DEV_KEY")
BASE_URL = "https://dev.to/api"

# Headers for authorization
headers = {"api-key": API_KEY, "Accept": "application/vnd.forem.api-v1+json"}


# Function to load articles into a DataFrame
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def load_articles_to_dataframe():
    """
    Loads all articles for a specific user into a pandas DataFrame.

    Parameters:
        username (str): The Dev.to username of the user.

    Returns:
        pandas.DataFrame: DataFrame containing article titles and created dates.
    """
    articles = []
    page = 1

    while True:
        response = requests.get(f"{BASE_URL}/articles/me?page={page}", headers=headers)

        # Check if the response was successful
        if response.status_code != 200:
            print(f"Failed to load articles: {response.status_code} - {response.text}")
            return pd.DataFrame(articles)

        data = response.json()

        # Break the loop if no more articles are found
        if not data:
            break

        # Append article data
        articles.extend(
            {"title": article["title"], "created_at": article["published_at"]}
            for article in data
        )
        page += 1

    # Convert to DataFrame
    return pd.DataFrame(articles)


# Function to load followers into a DataFrame
@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def load_followers_to_dataframe():
    """
    Loads all followers into a pandas DataFrame.

    Returns:
        pandas.DataFrame: DataFrame containing follower details.
    """
    followers = []
    page = 1

    while True:
        response = requests.get(
            f"{BASE_URL}/followers/users?page={page}&per_page=1000", headers=headers
        )

        # Check if the response was successful
        if response.status_code != 200:
            print(f"Failed to load followers: {response.status_code} - {response.text}")
            return pd.DataFrame(followers)

        data = response.json()

        # Break the loop if no more followers are found
        if not data:
            break

        # Append follower data
        followers.extend(data)
        page += 1

    return pd.DataFrame(followers)


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=5
)
def get_user_details(username):
    """
    Fetches additional user details by username, with retry and handling for 429 errors.

    Parameters:
        username (str): The Dev.to username of the follower.

    Returns:
        dict: A dictionary containing additional user details, including name,
              twitter handle, GitHub handle, location, joined date, and profile image.
    """
    url = f"{BASE_URL}/users/by_username?url={username}"

    while True:
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            data = response.json()
            return {
                "name": data.get("name"),
                "twitter_username": data.get("twitter_username"),
                "github_username": data.get("github_username"),
                "summary": data.get("summary"),
                "location": data.get("location"),
                "website_url": data.get("website_url"),
                "joined_at": data.get("joined_at"),
                "profile_image": data.get("profile_image"),
            }
        elif response.status_code == 429:
            print(f"Rate limit reached for {username}. Retrying after 1 second...")
            time.sleep(1)
        else:
            print(
                f"Failed to load user details for {username}: {response.status_code} - {response.text}"
            )
            return {}


def load_extended_followers_to_dataframe():
    """
    Loads all followers with additional details into a pandas DataFrame.

    This function first fetches basic follower information and then extends
    it by retrieving extra details for each follower, including location,
    social links, joined date, and profile image.

    Returns:
        pandas.DataFrame: DataFrame containing extended follower details.
    """
    # Load basic followers data
    followers_df = load_followers_to_dataframe()

    # Collect extended data
    extended_data = []
    for _, row in followers_df.iterrows():
        username = row["username"]
        user_details = get_user_details(username)

        # Merge basic and additional data
        follower_info = row.to_dict()
        follower_info.update(user_details)
        extended_data.append(follower_info)

    return pd.DataFrame(extended_data)
