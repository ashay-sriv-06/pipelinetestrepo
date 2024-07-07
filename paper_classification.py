#Code to extract papers from arxiv and then push the csv file to the github repository

import pandas as pd
from openai import OpenAI
import json
import requests
import xml.etree.ElementTree as ET
from urllib.parse import urlparse, parse_qs
import os
import tqdm
import arxiv
import time
from datetime import datetime, timedelta
from github import Github
import pytz

# Initialize OpenAI client
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Initialize GitHub client
g = Github(os.environ.get("GITHUB_TOKEN"))

def review_abstract_title_categorical(title: str, abstract: str, model: str) -> dict:
    """
    Rate the relevance of a paper to the topic of prompt engineering based on its title and abstract.
    """
    system_message = """You are a lab assistant, helping with a systematic review on prompt engineering. You've been asked to rate the relevance of a paper to the topic of prompt engineering.
    To be clear, this review will strictly cover hard prefix prompts. For clarification: Hard prompts have tokens that correspond directly to words in the vocab. For example, you could make up a new token by adding two together. This would no longer correspond to any word in the vocabulary, and would be a soft prompt
    Prefix prompts are prompts used for most modern transformers, where the model predicts the words after this prompt. In earlier models, such as BERT, models could predict words (e.g. <MASK>) in the middle of the prompt. Your job is to be able to tell whether a paper is related to (or simply contains) hard prefix prompting or prompt engineering. Please note that a paper might not spell out that it is using "hard prefix" prompting and so it might just say prompting. In this case, you should still rate it as relevant to the topic of prompt engineering.
    Please also note, that a paper that focuses on training a model as opposed to post-training prompting techniques is considered irrelevant. Provide a response in JSON format with two fields: 'reasoning' (a single sentence that justifies your reasoning) and 'rating' (a string that is one of the following categories: 'highly relevant', 'somewhat relevant', 'neutrally relevant', 'somewhat irrelevant', 'highly irrelevant') indicating relevance to the topic of prompt engineering)"""
    user_message = f"Title: '{title}', Abstract: '{abstract}'. Rate its relevance to the topic of prompt engineering as one of the following categories: 'highly relevant', 'somewhat relevant', 'neutrally relevant', 'somewhat irrelevant', 'highly irrelevant',  and provide text from the abstract that justifies your reasoning. Also provide this as a seperate column in the csv on a scale of 5 being most relevant and 1 being least relevant"

    response = client.chat.completions.create(
        model=model,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message},
        ],
    )

    try:
        content = json.loads(response.choices[0].message.content)
        rating = content.get("rating", "Not provided")
        reasoning = content.get("reasoning", "No reasoning provided")
        return {
            "Title": title,
            "Model": model,
            "Rating": rating,
            "Reasoning": reasoning,
        }
    except json.JSONDecodeError:
        return {
            "Title": title,
            "Model": model,
            "Error": "Invalid JSON response",
            "Response": response.choices[0].message.content,
        }

def fetch_recent_papers(max_results=30):
    """Fetch recent papers from arXiv."""
    search = arxiv.Search(
        query="cat:cs.CL OR cat:cs.AI",  # Categories for Computational Linguistics and Artificial Intelligence
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending
    )

    papers = list(search.results())

    return [{
        'title': paper.title,
        'authors': [author.name for author in paper.authors],
        'abstract': paper.summary,
        'pdf_url': paper.pdf_url,
        'published': paper.published.date()
    } for paper in papers]

def classify_papers(papers, model_name="gpt-3.5-turbo"):
    classified_papers = []
    for paper in tqdm.tqdm(papers, desc="Classifying papers"):
        result = review_abstract_title_categorical(
            title=paper['title'],
            abstract=paper['abstract'],
            model=model_name
        )
        paper.update(result)
        classified_papers.append(paper)

    # Sort papers by relevance
    relevance_order = {
        'highly relevant': 5,
        'somewhat relevant': 4,
        'neutrally relevant': 3,
        'somewhat irrelevant': 2,
        'highly irrelevant': 1
    }
    classified_papers.sort(key=lambda x: relevance_order.get(x['Rating'], 0), reverse=True)

    return classified_papers

def push_to_github(df, date):
    repo = g.get_repo("ashay-sriv-06/pipelinetestrepo")  # Replace with your repo name
    folder_name = f"paper_classifications_{date}"
    file_name = f"classified_papers_{date}.csv"
    file_path = f"{folder_name}/{file_name}"

    csv_content = df.to_csv(index=False)

    try:
        # Try to get the file (to update it if it exists)
        contents = repo.get_contents(file_path)
        repo.update_file(file_path, f"Update {file_name}", csv_content, contents.sha)
        print(f"Updated {file_path} in GitHub")
    except:
        # If the file doesn't exist, create it
        repo.create_file(file_path, f"Create {file_name}", csv_content)
        print(f"Created {file_path} in GitHub")

def run_paper_classification():
    current_date = datetime.now(pytz.utc).strftime('%Y-%m-%d')
    print(f"Starting classification run at {datetime.now(pytz.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC")

    recent_papers = fetch_recent_papers(max_results=30)  # Process 30 papers
    classified_papers = classify_papers(recent_papers)

    # Print results
    for paper in classified_papers:
        print(f"Title: {paper['title']}")
        print(f"Rating: {paper['Rating']}")
        print(f"Reasoning: {paper['Reasoning']}")
        print(f"Abstract: {paper['abstract'][:200]}...")  # Print first 200 characters of abstract
        print("\n---\n")

    # Create DataFrame and push to GitHub
    df = pd.DataFrame(classified_papers)
    push_to_github(df, current_date)

#def wait_until_midnight():
 #   now = datetime.now(pytz.utc)
  #  next_run = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
   # wait_seconds = (next_run - now).total_seconds()
    #print(f"Waiting {wait_seconds/3600:.2f} hours until next run at midnight UTC")
    #time.sleep(wait_seconds)

def main():
    #while True:
        run_paper_classification()
        #wait_until_midnight()

# Main execution
if __name__ == "__main__":
    main()