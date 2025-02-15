import os
import requests
import pandas as pd
import backoff
import time
from dotenv import load_dotenv
from bs4 import BeautifulSoup
import re
from typing import Dict, List, Set, Tuple

load_dotenv(override=True)
API_KEY = os.getenv("DEV_KEY")
BASE_URL = "https://dev.to/api"

headers = {"api-key": API_KEY, "Accept": "application/vnd.forem.api-v1+json"}


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def load_articles_to_dataframe() -> pd.DataFrame:
    """
    Loads all articles for authenticated user into a DataFrame.
    https://developers.forem.com/api/v1#tag/articles/operation/getUserArticles

    Returns:
        pd.DataFrame: DataFrame containing article titles and created dates.
    """
    articles = []
    page = 1

    while True:
        response = requests.get(f"{BASE_URL}/articles/me?page={page}", headers=headers)

        if response.status_code != 200:
            print(f"Failed to load articles: {response.status_code} - {response.text}")
            return pd.DataFrame(articles)

        data = response.json()

        if not data:
            break

        articles.extend(
            {
                "title": article["title"],
                "created_at": article["published_at"],
                "public_reactions_count": article["public_reactions_count"],
            }
            for article in data
        )
        page += 1

    return pd.DataFrame(articles)


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def load_followers_to_dataframe() -> pd.DataFrame:
    """
    Loads all followers into a DataFrame.
    https://developers.forem.com/api/v1#tag/followers/operation/getFollowers

    Returns:
        pd.DataFrame: DataFrame containing follower details.
    """
    followers = []
    page = 1

    while True:
        response = requests.get(
            f"{BASE_URL}/followers/users?page={page}&per_page=1000", headers=headers
        )

        if response.status_code != 200:
            print(f"Failed to load followers: {response.status_code} - {response.text}")
            return pd.DataFrame(followers)

        data = response.json()

        if not data:
            break

        followers.extend(data)
        page += 1

    return pd.DataFrame(followers)


@backoff.on_exception(
    backoff.expo, (requests.exceptions.RequestException,), max_tries=5
)
def get_user_details(username: str) -> Dict:
    """
    Fetches user details by username with retry for rate limits.
    https://developers.forem.com/api/v1#tag/users/operation/getUserMe

    Args:
        username: The Dev.to username of the follower.

    Returns:
        dict: Dictionary containing user details including name, social handles, location etc.
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
                "joined_at": data.get("joined_at"),  # when they joined dev.to
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


def load_users_with_details(users_df: pd.DataFrame = None) -> pd.DataFrame:
    """
    Loads user details (followers or winners) with additional profile information.

    If users_df is None, it loads the follower data first.

    Args:
        users_df (pd.DataFrame, optional): DataFrame containing usernames. If None, it defaults to followers.

    Returns:
        pd.DataFrame: DataFrame containing extended user details, including social profiles, location, and Dev.to metadata.
    """
    if users_df is None:
        users_df = load_followers_to_dataframe()

    extended_data = []
    for _, row in users_df.iterrows():
        username = row["username"]
        user_details = get_user_details(username)

        follower_info = row.to_dict()
        follower_info.update(user_details)
        extended_data.append(follower_info)

    return pd.DataFrame(extended_data)


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_user_articles_summary(username: str) -> Dict:
    """
    Fetches article metadata for a specific Dev.to user.

    Args:
        username (str): The Dev.to username of the user.

    Returns:
        Dict[str, Any]: A dictionary containing:
            - 'article_count' (int): Total number of articles.
            - 'article_titles' (List[str]): Titles of published articles.
            - 'unique_tags' (List[str]): Unique tags used across all articles.
            - 'tags' (List[List[str]]): List of tag lists for each article.
            - 'article_reading_time_minutes' (List[int]): Reading time for each article.
            - 'article_comments_counts' (List[int]): Number of comments on each article.
            - 'article_positive_reactions_counts' (List[int]): Number of positive reactions per article.
            - 'article_published_at' (List[str]): Publish dates of the articles.
    """
    url = f"{BASE_URL}/articles?username={username}"
    headers = {"api-key": API_KEY, "Accept": "application/vnd.forem.api-v1+json"}

    article_titles = []
    article_reading_time_minutes = []
    unique_tags: Set[str] = set()
    article_comments_counts = []
    article_positive_reactions_counts = []
    article_published_at = []
    tags = []
    page = 1

    while True:
        response = requests.get(f"{url}&page={page}", headers=headers)

        if response.status_code == 200:
            articles = response.json()
            if not articles:
                break

            for article in articles:
                print(article)
                article_titles.append(article.get("title"))
                unique_tags.update(article.get("tag_list", []))
                tags.append(article.get("tag_list", []))
                article_reading_time_minutes.append(article.get("reading_time_minutes"))
                article_comments_counts.append(article.get("comments_count"))
                article_published_at.append(article.get("published_at"))
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
            return {
                "article_count": 0,
                "article_titles": [],
                "unique_tags": [],
                "tags": [],
                "article_reading_time_minutes": [],
                "article_comments_counts": [],
                "article_positive_reactions_counts": [],
                "article_published_at": [],
            }

    return {
        "article_count": len(article_titles),
        "article_titles": article_titles,
        "unique_tags": list(unique_tags),
        "tags": tags,
        "article_reading_time_minutes": article_reading_time_minutes,
        "article_comments_counts": article_comments_counts,
        "article_positive_reactions_counts": article_positive_reactions_counts,
        "article_published_at": article_published_at,
    }


def update_followers_with_articles(followers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Updates the followers DataFrame with article-related metrics.

    This function adds the following columns to the DataFrame:
    - 'article_count': Total number of articles published by the user.
    - 'article_titles': List of article titles published by the user.
    - 'unique_tags': List of distinct tags used across all articles.
    - 'tags': List of tags for each article.
    - 'article_reading_time_minutes': List of reading times for each article.
    - 'article_comments_counts': List of comment counts for each article.
    - 'article_positive_reactions_counts': List of positive reactions per article.
    - 'article_published_at': List of article publish dates.

    Args:
        followers_df (pd.DataFrame): The followers DataFrame.

    Returns:
        pd.DataFrame: Updated DataFrame containing article-related information for each follower.
    """
    article_counts = []
    article_titles = []
    unique_tags = []
    article_reading_time_minutes = []
    article_comments_counts = []
    article_positive_reactions_counts = []
    article_published_at = []
    tags = []

    for username in followers_df["username"]:
        article_summary = get_user_articles_summary(username)

        article_counts.append(article_summary["article_count"])
        article_titles.append(article_summary["article_titles"])
        unique_tags.append(article_summary["unique_tags"])
        tags.append(article_summary["tags"])
        article_reading_time_minutes.append(
            article_summary["article_reading_time_minutes"]
        )
        article_comments_counts.append(article_summary["article_comments_counts"])
        article_positive_reactions_counts.append(
            article_summary["article_positive_reactions_counts"]
        )
        article_published_at.append(article_summary["article_published_at"])
        print(
            f"For {username} found {article_summary["article_count"]} articles {article_summary["article_titles"]}  with {article_summary["unique_tags"]} tags with {article_summary["article_reading_time_minutes"]}, {article_summary["article_comments_counts"]}, {article_summary["article_positive_reactions_counts"]}"
        )

    followers_df["article_count"] = article_counts
    followers_df["article_titles"] = article_titles
    followers_df["unique_tags"] = unique_tags
    followers_df["tags"] = tags
    followers_df["article_reading_time_minutes"] = article_reading_time_minutes
    followers_df["article_comments_counts"] = article_comments_counts
    followers_df["article_positive_reactions_counts"] = (
        article_positive_reactions_counts
    )
    followers_df["article_published_at"] = article_published_at

    return followers_df


@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=5)
def get_user_stats(username: str) -> Tuple[List[str], List[str], int, int]:
    """
    Scrapes user profile statistics from the Dev.to website.

    Args:
        username (str): The Dev.to username.

    Returns:
        Tuple:
            - List[str]: Titles of user badges.
            - List[str]: Descriptions of user badges.
            - int: Number of comments written by the user.
            - int: Number of tags followed by the user.
    """
    url = f"https://dev.to/{username}/"
    response = requests.get(url, timeout=10)
    response.raise_for_status()

    if response is None:
        return [], [], 0, 0

    soup = BeautifulSoup(response.text, "html.parser")

    badges = []
    badge_descriptions = []
    badge_elements = soup.find_all("div", class_="badge_text_content")

    # scrap badges
    for badge in badge_elements:
        badge_title = badge.find("h4", class_="title fw-800 fs-l").text.strip()
        badge_description = badge.find("p", class_="description").text.strip()
        badges.append(badge_title)
        badge_descriptions.append(badge_description)

    # scrap comments count
    comment_count = 0
    for div in soup.find_all("div", class_="flex items-center mb-4"):
        if "comments written" in div.get_text(strip=True):
            comment_count = int(re.search(r"\d+", div.get_text(strip=True)).group())

    # scrap tags count
    tags_count = 0
    for div in soup.find_all("div", class_="flex items-center"):
        text = div.get_text(strip=True)
        if "tags followed" in text:
            tags_count = int(re.search(r"\d+", text).group())

    return badges, badge_descriptions, comment_count, tags_count


def update_followers_with_stats(followers_df: pd.DataFrame) -> pd.DataFrame:
    """
    Updates followers DataFrame with profile statistics.

    This function adds the following columns:
    - 'badges': List of user badges.
    - 'badge_descriptions': Descriptions of earned badges.
    - 'comments_count': Number of comments written by the user.
    - 'tags_count': Number of tags followed by the user.

    Args:
        followers_df (pd.DataFrame): The DataFrame containing follower usernames.

    Returns:
        pd.DataFrame: Updated DataFrame with additional statistics.
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

    followers_df["badges"] = badges_list
    followers_df["badge_descriptions"] = badge_descriptions_list
    followers_df["comments_count"] = comments_count_list
    followers_df["tags_count"] = tags_count_list

    return followers_df
