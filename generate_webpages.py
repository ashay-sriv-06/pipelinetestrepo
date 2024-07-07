#v2 of github solution that is working properly
#Code for generating a webpage and commiting it to github[ more suited for when the csv is stored locally]
import pandas as pd
import os
from datetime import datetime
from github import Github
import sys
import pytz
from io import StringIO

def create_webpage(paper):
    """Create HTML content for a single paper."""
    title = paper['title']
    date = paper['published']
    authors = paper['authors']
    summary = paper['abstract']
    reasoning = paper['Reasoning']
    pdf_url = paper['pdf_url']

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #333; }}
            .authors {{ font-style: italic; color: #666; margin-bottom: 20px; }}
            .summary, .reasoning {{ background-color: #f9f9f9; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
            .paper-link {{ display: inline-block; background-color: #4CAF50; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
            .paper-link:hover {{ background-color: #45a049; }}
            .ai-notice {{ font-size: 0.8em; text-align: right; margin-top: 20px; color: #999; }}
        </style>
    </head>
    <body>
        <h1>{title}</h1>
        <p><strong>Date:</strong> {date}</p>
        <p class="authors"><strong>Authors:</strong> {authors}</p>
        <div class="summary">
            <h2>Abstract</h2>
            <p>{summary}</p>
        </div>
        <div class="reasoning">
            <h2>AI-Generated Summary</h2>
            <p>{reasoning}</p>
        </div>
        <a href="{pdf_url}" class="paper-link" target="_blank">Read the full paper</a>
        <p class="ai-notice">The summary is AI-generated and may not perfectly reflect the paper's content.</p>
    </body>
    </html>
    """

    return html_content



def commit_to_github(repo, file_path, content, commit_message):
    """Commit a file to the GitHub repository."""
    try:
        try:
            contents = repo.get_contents(file_path)
            repo.update_file(contents.path, commit_message, content, contents.sha)
            print(f"Updated {file_path}")
        except Exception as e:
            if "404" in str(e):  # File doesn't exist yet
                repo.create_file(file_path, commit_message, content)
                print(f"Created {file_path}")
            else:
                raise
        return True
    except Exception as e:
        print(f"Error committing {file_path}: {str(e)}")
        return False

def get_csv_content(repo, path):
    contents = repo.get_contents(path)
    if isinstance(contents, list):
        # If it's a directory, find the CSV file
        csv_file = next((file for file in contents if file.name.endswith('.csv')), None)
        if csv_file is None:
            raise FileNotFoundError(f"No CSV file found in {path}")
        return csv_file.decoded_content.decode()
    else:
        # If it's a file, return its content
        return contents.decoded_content.decode()

def main():
    # GitHub setup
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Please set the GITHUB_TOKEN environment variable.")
        sys.exit(1)

    g = Github(github_token)
    repo = g.get_repo("ashay-sriv-06/pipelinetestrepo")  # Replace with your repo name

    print("Contents of the repository root:")
    for content in repo.get_contents(""):
        print(content.path)

    # Get today's date
    today = datetime.now(pytz.utc).strftime('%Y-%m-%d')

    # Try to find today's CSV file
    csv_content = None
    csv_path = None
    possible_paths = [
        f"paper_classifications_{today}",
        f"paper_classifications_{today}.csv",
    ]

    for path in possible_paths:
        try:
            csv_content = get_csv_content(repo, path)
            csv_path = path
            print(f"Found CSV file at: {path}")
            break
        except Exception as e:
            print(f"Error accessing {path}: {str(e)}")

    if csv_content is None:
        print(f"Could not find CSV file for {today}.")
        print("Please ensure that:")
        print("1. There are CSV files in your repository.")
        print("2. You have the correct permissions to access the repository.")
        return

    try:
        # Read the CSV content
        df = pd.read_csv(StringIO(csv_content))

        # Filter for highly relevant papers
        highly_relevant = df[df['Rating'] == 'highly relevant']
        print(f"Found {len(highly_relevant)} highly relevant papers.")

        # Create a folder for today's webpages
        webpage_folder = f"paper_webpages_{today}"

        # Create and commit webpages for each highly relevant paper
        successful_commits = 0
        for _, paper in highly_relevant.iterrows():
            html_content = create_webpage(paper)

            # Create a filename from the title
            title = paper['title']
            filename = ''.join(e for e in title if e.isalnum() or e.isspace()).rstrip()
            filename = filename.replace(' ', '_').lower()[:50]  # Limit filename length
            file_path = f"{webpage_folder}/{filename}.html"

            commit_message = f"Add webpage for paper: {title}"
            if commit_to_github(repo, file_path, html_content, commit_message):
                successful_commits += 1

        print(f"Finished processing. Successfully committed {successful_commits} out of {len(highly_relevant)} webpages to GitHub for {today}.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")
        print(f"Could not process the CSV file: {csv_path}")

if __name__ == "__main__":
    main()