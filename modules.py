import json
from langdetect import detect, DetectorFactory, LangDetectException
import re
from datetime import datetime
import pytz
import hashlib
from pymongo import MongoClient
from bson import ObjectId
import logging
from urllib.parse import quote
from argostranslate import package, translate
import argostranslate.package, argostranslate.translate
from telethon.errors import FloodWaitError

logger = logging.getLogger('telegram_scraper')
logger.setLevel(logging.DEBUG)

if not logger.hasHandlers():
    fh = logging.FileHandler('telegram_scraper.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    
def read_config(filename):
    try:
        with open(filename, 'r') as config_file:
            config = json.load(config_file)
        return config
    except FileNotFoundError:
        logging.error(f"Config file '{filename}' not found.")
        return None
    except json.JSONDecodeError:
        logging.error(f"Error decoding JSON file: {filename}")
        return None

def hash_sha256(content):
    # Serialize the dictionary in a consistent manner using JSON
    serialized_content = json.dumps(content, sort_keys=True)
    # Hash the serialized content using SHA-256
    return hashlib.sha256(serialized_content.encode('utf-8')).hexdigest()
    
def extract_urls_from_text(text):
    # Regular expression pattern for matching URLs
    url_pattern = re.compile(r'https?://\S+')

    # Find all matches in the text
    urls = re.findall(url_pattern, text)

    return urls


def translate_to_english(text):
    try:
        if not text:
            return text
        detected_language = detect(text)
        if detected_language == "zh-cn":
            detected_language = "zh"
        
        if detected_language == 'en':
            return text

        installed_languages = translate.get_installed_languages()
        source_lang_code = next((lang.code for lang in installed_languages if lang.code == detected_language), None)
        
        if source_lang_code is None:
            raise ValueError(f"Language '{detected_language}' is not supported.")
        
        translation = translate.translate(text, source_lang_code, 'en')
        return translation
    except:
        return text


def datetime_to_string(dt):
    """ Convert datetime object to string. """
    return dt.isoformat()

def insert_into_mongo(data_list, database, collection_db, unique_identifier, second_unique_identifier=None):
    config = read_config("config.json")
    mongo_uri = config.get("mongo_uri")
    try:
        if isinstance(data_list, str):
            # If data_list is a string, parse it as JSON
            data_list = json.loads(data_list)

        if isinstance(data_list, dict):
            data_list = [data_list]  # Wrap the dictionary in a list

        client = MongoClient(mongo_uri)
        db = client[database]
        collection = db[f"{collection_db}"]

        # Create index based on the presence of a second unique identifier
        if second_unique_identifier:
            collection.create_index([(f"{unique_identifier}", 1), (f"{second_unique_identifier}", 1)], unique=True)
        else:
            collection.create_index([(f"{unique_identifier}", 1)], unique=True)

        for data in data_list:
            # Construct query based on the provided unique identifiers
            if second_unique_identifier:
                query = {f"{unique_identifier}": data[f"{unique_identifier}"],
                         f"{second_unique_identifier}": data[f"{second_unique_identifier}"]}
            else:
                query = {f"{unique_identifier}": data[f"{unique_identifier}"]}

            update = {"$set": data}
            collection.update_one(query, update, upsert=True)

        logger.info("Data updated/inserted successfully into MongoDB.")
        return True
    except Exception as e:
        logger.error(f"Failed to update/insert data into MongoDB. Error: {e}")
        return False


def retrieve_key_from_document(collection_name, unique_key, unique_value, target_key, database):
    """
    Retrieve a specific key from a document in a MongoDB collection.
    :param collection_name: The name of the collection.
    :param unique_key: The key used for identifying the unique document.
    :param unique_value: The value of the unique key.
    :param target_key: The key to retrieve from the document.
    :return: The value of the target key, or None if not found.
    """
    config = read_config("config.json")
    mongo_uri = config.get("mongo_uri")
    client = MongoClient(mongo_uri)
    db = client[database]
    collection = db[collection_name]

    # Adjust the query based on whether the unique identifier is an ObjectId or not
    if unique_key == "_id":
        unique_value = ObjectId(unique_value)

    query = {unique_key: unique_value}
    document = collection.find_one(query, {target_key: 1, '_id': 0})

    if document:
        return document.get(target_key)
    else:
        return None

def retrieve_key_list(collection_name, unique_key, database):
    config = read_config("config.json")
    mongo_uri = config.get("mongo_uri")
    client = MongoClient(mongo_uri)  # Connect to MongoDB
    db = client[database]  # Connect to the database
    collection = db[collection_name]  # Connect to the collection

    list = []
    for document in collection.find():  # Iterate over all documents
        if unique_key in document:  # Check if 'subforum_link' key exists
            list.append(document[unique_key])  # Add the value to the list

    return list

def find_one_document(key, value, collection_name, database):
    config = read_config("config.json")
    mongo_uri = config.get("mongo_uri")
    client = MongoClient(mongo_uri)  # Connect to MongoDB
    db = client[database]  # Connect to the database
    collection = db[collection_name]  # Connect to the collection
    query = {key: value}
    # If the query is based on '_id' and is a string, convert it to ObjectId
    if '_id' in query and isinstance(query['_id'], str):
        query['_id'] = ObjectId(query['_id'])

    return collection.find_one(query)


def update_post_counts(num_new_posts, key, value, collection, database):
    # Retrieve the tracking document
    query = {key: value}
    key_name = list(query.keys())[0]
    tracking_data = find_one_document(key, value, collection, database)
    tracking_data['daily'] += num_new_posts
    tracking_data['weekly'] += num_new_posts
    tracking_data['monthly'] += num_new_posts
    tracking_data['total'] += num_new_posts
    tracking_data['last_updated'] = datetime_to_string(datetime.now(pytz.utc))
    tracking_data.pop('_id', None)

    insert_into_mongo(tracking_data, database, collection, key_name)

def contains_any_word(text, words):
    """
    Check if any of the words in the list 'words' is present in 'text'.
    The search is case-insensitive and will match words irrespective of their position.

    :param text: str - The text to search in.
    :param words: list - The list of words to search for.
    :return: bool - True if any word is found, False otherwise.
    """
    for word in words:
        # Create a regular expression pattern for the word
        # \b represents a word boundary, so that partial matches are avoided
        # re.IGNORECASE makes the search case-insensitive
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False
