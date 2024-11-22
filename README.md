The **Dev.to Audience Analyzer** is a Python tool that helps Dev.to authors understand more about their followers. It gives you insights into who your followers are, how active they are, and whether they seem like real, engaged users.

This GitHub project was created as part of my blog post [Who's Really Following You on Dev.to? A Guide to Analyzing Your Audience](https://dev.to/olgabraginskaya/whos-really-following-you-on-devto-a-guide-to-analyzing-your-audience-1c0m), where I share insights and tools to analyze the composition and engagement of my followers.

### What This Project Does

With this tool, you can look at your followers in different ways, including:

1. **Activity Levels**: See if followers are writing articles, leaving comments, or just passively following.
2. **Profile Completeness**: Find out which followers have filled out their profiles with details like bio, location, GitHub, or Twitter links.
3. **Engagement Patterns**: Discover which articles attracted the most followers and spot trends in follower growth after you publish new content.
4. **Possible Bots or Inactive Accounts**: Spot any patterns, like many followers joining Dev.to and following you on the same day, which could indicate low engagement or potential bot behavior.

### Requirements

To use this project, you'll need:

1. A **Dev.to API Key** (required) to access your follower information on Dev.to which you can find [here](https://dev.to/settings/extensions) under DEV Community API Keys.
2. A **GitHub Token** (optional) for extended analysis, specifically for followers who have linked their GitHub profiles [details](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens).

### Project Overview

- **`analysis.ipynb`**: This Jupyter notebook contains all the code for performing the analysis. You can run this notebook to view visualizations and dive deeper into your follower data.
- **`src/api_client.py`**: This script handles interactions with the Forem API, allowing the tool to retrieve follower information from Dev.to. The Forem API documentation can be found [here](https://developers.forem.com/api/v1#tag/users/operation/getUserMe).
- **`src/github_client.py`**: This script handles interactions with the [Github API](https://docs.github.com/en/rest?apiVersion=2022-11-28), specifically for analyzing GitHub-linked followers.

### Development Setup

Follow these steps to set up your development environment:

1. **Clone the repository**:

```bash
git clone https://github.com/olgazju/blog_dev_to_audience_analyzer.git
cd blog_dev_to_audience_analyzer
```

2. **Create and activate a virtual environment**:

```bash
brew update && brew install pyenv pyenv-virtualenv
pyenv install 3.12.2
pyenv virtualenv 3.12.2 blog_dev_to_audience_analyzer
pyenv local blog_dev_to_audience_analyzer
```

3.  **Install the required dependencies**:

```bash
pip install -r requirements.txt
```

4. **Install and configure pre-commit hooks**:

```bash
pip install pre-commit
pre-commit install
```

5. **Run pre-commit hooks manually (optional)**:

```bash
pre-commit run --all-files
```

### Setup

1. Create a `.env` file in the root of the project with the following format:

```makefile
DEV_KEY=your_devto_api_key
GITHUB_TOKEN=your_github_token
```

Replace `your_devto_api_key` and `your_github_token` with your actual Dev.to API key and GitHub token.

2. Run the `analysis.ipynb` notebook to perform the analysis. The notebook will retrieve data from Dev.to using the Forem API and, if available, from GitHub for further analysis on linked profiles.

This project will help you uncover valuable insights about your Dev.to audience, so you can make data-driven decisions about your content and engagement strategy.

### Analysis

This tool provides valuable insights into follower engagement by analyzing activity patterns after each article publication.

This plot shows the pattern of my new followers gained over time along with the cumulative follower count, marked against the dates of article publications. The teal bars represent the number of new followers on each day, while the orange line tracks the cumulative follower growth. Noticeable spikes in new followers align closely with specific article publication dates, suggesting that certain articles have significantly boosted follower acquisition. This visualization helps in understanding how content impacts audience growth over time, with clear peaks following key publications.

![image](https://github.com/user-attachments/assets/aa87d63b-1c06-47c0-a791-c408cb55d1f3)

The chart below shows the distribution of my new followers by category within 14 days of each article's release.

![image](https://github.com/user-attachments/assets/3d03a2cf-c0d7-451c-960d-ae6902d4c76d)
