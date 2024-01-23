# -*- coding: utf-8 -*-
"""NLP Final Project Felix Marco.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1BpupW1NGjfepzSL49aKJ3Ctb-0IMoYSw

# Final Project Natural Language Processing.

Script consists of 2 major sections
1. Running model inference on user input -> returning academic researchers / groups based on research interest

2. (Training and) fine-tuning LLM based on custom dataset


While step 1 relies on step 2, both steps should not be run together, as model training needs to be done only once.
"""

# Install
#!pip install transformers
#!pip install pycountry

# Imports
import requests
from transformers import pipeline
import nltk
from nltk.corpus import stopwords
import pycountry
from typing import List, Dict

nltk.download('punkt')
nltk.download('stopwords')

def anwser_question(context:str, question:str):
  '''
  Asks the qa_model to answer a given question based on the passed context.
  It then splits the answer to return each individual information after also removing the stop words.

  :param context: The query from the user.

  :param question: The question to be asked to the model about the query of the user.
  '''
  qa_model = pipeline("question-answering", "timpal0l/mdeberta-v3-base-squad2")
  split_context = nltk.sent_tokenize(context)

  answers = []
  for c in split_context:
    answers.append(qa_model(question = question, context = c))

  infos = [answer['answer'] for answer in answers if answer['score'] > 0.15]
  filtered_infos = remove_stop_words(infos)

  return filtered_infos


def extract_information(context:str):
  '''
  Extracts the topics and the locations from the given context.

  :param context: The query from the user.
  '''

  topics = anwser_question(context, "What am I interested in?")
  locations = anwser_question(context, "Which country am I interested in?")

  return topics, locations

def remove_stop_words(topics:List[str]):
  '''
  This function removes the stop words from a given list of topics.
  Each topic is an answer previously generated by the qa_model.
  For each topic it removes the english stop words and then it perform a word tokenization.
  The return is a list of all the single topics found in the answer of the qa_model stripped
  by stopwords and punctuation.

  :param topics: list of the answers returned by the qa_model
  '''
  stop_words = set(stopwords.words('english'))
  stop_words.update(['.', ',', ';'])

  all_topics = []
  for topic in topics:
    word_tokens = nltk.word_tokenize(topic)
    current_topic = []

    for word in word_tokens:
      if word.lower() not in stop_words:
        current_topic.append(word)
      else:
        if len(current_topic) > 0:
          all_topics.append(current_topic)
          current_topic = []

    if len(current_topic) > 0:
        all_topics.append(current_topic)

  all_topics = [" ".join(topic) for topic in all_topics]
  return all_topics

def get_concepts(topic:str):
  '''
  This function return a list of concepts given a single topic as input.
  It performs an API call to OpenAlex to retrieve the correlated concepts object to that particular topic.
  Then a list of concepts each with its own ID, display name, relevance score, description and cited_by_count is returned.

  :param topic: A single topic from which the correlated concepts should be retrieved.
  '''
  # pass topic to openAlex API
  results = requests.get(f'https://api.openalex.org/concepts?search={topic}').json()['results']
  print("Number of concepts found: ", len(results))

  # create concept dictionaries
  keys = ['id', 'display_name', 'relevance_score', 'description', 'cited_by_count']
  concepts = [dict(zip(keys, [result[key] for key in keys])) for result in results]
  return concepts

def get_authors(concepts: List[Dict[str, str]], country_code: Union[str, None]:
  '''
  Builds a list of 100 authors that belong to one of the specified concepts and
  to the country code by querying openAlex
  The returned authors are built as a dictionary, containing interesting characteristics.
  The returned authors are sorted by the number of citation in the last 2 years.
  This can be done as the concepts passed to the function are assumed to be all related,
  therefore authors can be directly compared.

  :param concepts: list of concepts dicts, all concepts are part of the same 'topic'
  :param country_code: code of the country an author's last known institution should be in,
      can be None
  '''

  all_authors = []
  for concept in concepts:

    # build filter. Either contains country code param or not
    filter = f"filter=concept.id:{concept['id']}"
    if country_code is not None:
      filter += f",last_known_institution.country_code:{country_code}"

    # make request
    authors  = requests.get(f"https://api.openalex.org/authors?{filter}&per-page=100&sort=cited_by_count:desc").json()['results']
    for a in authors:
      author = {}
      author['display_name'] = a['display_name']
      author['cited_by_count'] = a['cited_by_count']
      author['works_count'] = a['works_count']
      author['citing_score'] = a['cited_by_count'] / a['works_count']
      author['2yr_mean_citedness'] = a['summary_stats']['2yr_mean_citedness']
      lki = a.get('last_known_institution', None)
      if lki is not None:
        author['association'] = lki['display_name']
      else:
        author['association'] = 'No institution'
      all_authors.append(author)

  # sort and return
  return sorted(all_authors, key=lambda x: (-1 * x["2yr_mean_citedness"], -1 * x["cited_by_count"]))

def convert_location_to_alpha2(countries):
  '''
  Converts a given list of countries to their ISO 3166-1 alpha-2 representation.
  This is done using the pycountry library. If a given country can not be resolved,
  It is removed from the result. Example: ["Germany", "Tomato", "Italy"] -> ["DE", "IT"]

  :param countries: List of country names as strings
  '''
  codes = [pycountry.countries.get(name = country) for country in countries]
  filtered_codes = [code.alpha_2 for code in codes if code is not None]
  return filtered_codes if len(filtered_codes) > 0 else [None]

def print_authors(authors, country_code):
  '''
  Prints the country_code and the given authors nicely to the console.
  Uses some basic formatting to achieve nice looking results.

  :param authors: list of dictionaries describing authors
  :param country_code: code of a country (e.g. 'DE'), can be None
  '''
  if country_code is not None:
    print(f"\nIn {pycountry.countries.get(alpha_2=country_code).name}:")

  for author in authors:
    print(f"\n{author['display_name']} - {author['association']}")
    print("   • Avg number of citations last 2yrs: ", author['2yr_mean_citedness'])
    print("   • Number of works: ", author['works_count'])
    print("   • Number of citations: ", author['cited_by_count'])
    print("   • Citing score: ", author['citing_score'])

# extract topics from the user input query
topics, locations = extract_information("I'm interested in Computer Science and Botanic in France, Germany and Italy")
print("The inferred topics are:", ", ".join(topics))
print("The inferred locations are:", ", ".join(locations))

# if no topics are inferred, we abort
if len(topics) != 0:

  for topic in topics:
    # get concepts based on topics
    concepts = get_concepts(topic)

    # get country_codes based on inferred locations
    # to ensure the below for loop runs once when no locations are specified,
    # convert_location_to_alpha2 returns [None] when locations are empty.
    country_codes = convert_location_to_alpha2(locations)
    print(f'Results for the topic: "{topic}"')
    for country_code in country_codes:
      # get authors for the first 5 concepts and the country code
      authors = get_authors(concepts[:5], country_code)
      # print first 5 authors and the country code
      print_authors(authors[:5], country_code)
      print('\n\n')
else:
  print("No topics found!")
