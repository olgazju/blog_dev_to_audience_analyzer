import os
import requests
import pandas as pd
import backoff
from time import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re

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
            {
                "title": article["title"],
                "created_at": article["published_at"],
                "public_reactions_count": article["public_reactions_count"],
            }
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


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_user_articles_summary(username):
    """
    Fetches a summary of articles for a given user, including article count, titles, and unique tags.

    Parameters:
        username (str): The Dev.to username of the user.

    Returns:
        dict: A dictionary with keys 'article_count', 'article_titles', and 'unique_tags'.
    """
    url = f"{BASE_URL}/articles?username={username}"
    headers = {"api-key": API_KEY, "Accept": "application/vnd.forem.api-v1+json"}

    article_titles = []
    article_reading_time_minutes = []
    unique_tags = set()  # Use a set to ensure tags are unique
    article_comments_counts = []
    article_positive_reactions_counts = []
    page = 1

    while True:
        response = requests.get(f"{url}&page={page}", headers=headers)

        if response.status_code == 200:
            articles = response.json()
            if not articles:
                break

            # Process each article
            for article in articles:
                print(article)
                article_titles.append(article.get("title"))
                unique_tags.update(article.get("tag_list", []))
                article_reading_time_minutes.append(article.get("reading_time_minutes"))
                article_comments_counts.append(article.get("comments_count"))
                article_positive_reactions_counts.append(
                    article.get("positive_reactions_count")
                )
            page += 1
        elif response.status_code == 429:
            print(f"Rate limit reached for {username}. Retrying after 1 second...")
            time.sleep(1)
        else:
            print(
                f"Failed to load articles for {username}: {response.status_code} - {response.text}"
            )
            return {"article_count": 0, "article_titles": [], "unique_tags": []}

    return {
        "article_count": len(article_titles),
        "article_titles": article_titles,
        "unique_tags": list(unique_tags),
        "article_reading_time_minutes": article_reading_time_minutes,
        "article_comments_counts": article_comments_counts,
        "article_positive_reactions_counts": article_positive_reactions_counts,
    }


def update_followers_with_articles(followers_df):
    """
    Updates the followers DataFrame with article information for each follower.

    This function adds three new columns to the DataFrame:
    - 'article_count': Total number of articles published by the user.
    - 'article_titles': List of article titles published by the user.
    - 'unique_tags': List of distinct tags used across all articles.

    Parameters:
        followers_df (pd.DataFrame): The followers DataFrame.

    Returns:
        pd.DataFrame: Updated DataFrame with article information.
    """
    # Initialize lists to store article information
    article_counts = []
    article_titles = []
    unique_tags = []
    article_reading_time_minutes = []
    article_comments_counts = []
    article_positive_reactions_counts = []

    # Loop through each follower and fetch their article summary
    for username in followers_df["username"]:
        article_summary = get_user_articles_summary(username)

        # Append the information to the lists
        article_counts.append(article_summary["article_count"])
        article_titles.append(article_summary["article_titles"])
        unique_tags.append(article_summary["unique_tags"])
        article_reading_time_minutes.append(
            article_summary["article_reading_time_minutes"]
        )
        article_comments_counts.append(article_summary["article_comments_counts"])
        article_positive_reactions_counts.append(
            article_summary["article_positive_reactions_counts"]
        )

        print(
            f"For {username} found {article_summary["article_count"]} articles {article_summary["article_titles"]}  with {article_summary["unique_tags"]} tags with {article_summary["article_reading_time_minutes"]}, {article_summary["article_comments_counts"]}, {article_summary["article_positive_reactions_counts"]}"
        )

    # Add the new columns to the DataFrame
    followers_df["article_count"] = article_counts
    followers_df["article_titles"] = article_titles
    followers_df["unique_tags"] = unique_tags
    followers_df["article_reading_time_minutes"] = article_reading_time_minutes
    followers_df["article_comments_counts"] = article_comments_counts
    followers_df["article_positive_reactions_counts"] = (
        article_positive_reactions_counts
    )

    return followers_df


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_user_stats(username):
    """
    Fetches a user's badges, comments count, and tags followed count from DEV.to.

    Args:
        username (str): The DEV.to username.

    Returns:
        tuple: A tuple containing lists of badge titles and descriptions, comment count, and tags count.
    """
    url = f"https://dev.to/{username}/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # Raise HTTPError for bad responses

    if response is None:
        return [], [], 0, 0  # Return default empty values if request fails

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract badges and descriptions
    badges = []
    badge_descriptions = []
    badge_elements = soup.find_all("div", class_="badge_text_content")

    for badge in badge_elements:
        badge_title = badge.find("h4", class_="title fw-800 fs-l").text.strip()
        badge_description = badge.find("p", class_="description").text.strip()
        badges.append(badge_title)
        badge_descriptions.append(badge_description)

    # Extract comments written count
    comment_count = 0
    for div in soup.find_all("div", class_="flex items-center mb-4"):
        if "comments written" in div.get_text(strip=True):
            comment_count = int(re.search(r"\d+", div.get_text(strip=True)).group())

    # Extract tags followed count
    tags_count = 0
    for div in soup.find_all("div", class_="flex items-center"):
        text = div.get_text(strip=True)
        if "tags followed" in text:
            tags_count = int(re.search(r"\d+", text).group())

    return badges, badge_descriptions, comment_count, tags_count


def update_followers_with_stats(followers_df):
    """
    Updates the extended followers DataFrame with additional columns for badges, badge descriptions,
    comments count, and tags followed count by fetching each follower's DEV.to profile.

    Args:
        followers_df (pd.DataFrame): The DataFrame containing follower usernames and article titles.

    Returns:
        pd.DataFrame: The updated DataFrame with new columns for badges, badge descriptions,
                      comments count, and tags followed count.
    """
    badges_list = []
    badge_descriptions_list = []
    comments_count_list = []
    tags_count_list = []

    for username, article_titles in zip(
        followers_df["username"], followers_df["article_titles"]
    ):
        badges, badge_descriptions, comments_count, tags_count = get_user_stats(
            username
        )
        print(
            username,
            article_titles,
            badges,
            badge_descriptions,
            comments_count,
            tags_count,
        )
        badges_list.append(badges)
        badge_descriptions_list.append(badge_descriptions)
        comments_count_list.append(comments_count)
        tags_count_list.append(tags_count)

    # Add new columns to the DataFrame
    followers_df["badges"] = badges_list
    followers_df["badge_descriptions"] = badge_descriptions_list
    followers_df["comments_count"] = comments_count_list
    followers_df["tags_count"] = tags_count_list

    return followers_df
