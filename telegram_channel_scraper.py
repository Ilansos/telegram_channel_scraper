from datetime import datetime
import pytz
import random
import os
import logging
from modules import contains_any_word, datetime_to_string, hash_sha256, read_config, extract_urls_from_text, find_one_document, insert_into_mongo, translate_to_english, update_post_counts
from telethon import TelegramClient, events, sync, errors
import asyncio
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.channels import GetParticipantsRequest
from telethon.tl.types import ChannelParticipantsSearch
from telethon.errors import FloodWaitError


logger = logging.getLogger('telegram_scraper')
logger.setLevel(logging.DEBUG)

if not logger.hasHandlers():
    fh = logging.FileHandler('telegram_scraper.log')
    fh.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

with open('keywords.txt', 'r') as file:
    # Read the file content and split by new lines
    word_list = file.read().splitlines()

with open('channel_list.txt', 'r') as file:
    # Read the file content and split by new lines
    channel_usernames = file.read().splitlines()

config = read_config("config.json")
api_id = config.get("telegram_api_id")
api_hash = config.get("telegram_api_hash")
client = TelegramClient('new_session_name', api_id, api_hash)

def extract_channel_details(channel_details, channel_username):
    Channel_Name = channel_details.chats[0].title
    Channel_ID = channel_details.chats[0].id
    Description = channel_details.full_chat.about
    description_in_english = translate_to_english(Description)
    urls_in_description = extract_urls_from_text(Description)
    Subscribers = channel_details.full_chat.participants_count
    # Constructing the URL
    if channel_details.chats[0].username:
        channel_url = f"https://t.me/{channel_details.chats[0].username}"
    else:
        channel_url = channel_username
    
    try:
        existing_document = find_one_document('channel_username', channel_username, 'channel_main_info', 'tg_scrapers')
        daily = existing_document.get('daily')
        weekly = existing_document.get('weekly')
        monthly = existing_document.get('monthly')
        total = existing_document.get('total')
        last_updated = existing_document.get('last_updated')
        channel_info = {"channel_username": channel_username, "channel_name": Channel_Name, "channel_id": Channel_ID, "description": Description, "description_in_english": description_in_english, "urls_in_description": urls_in_description, "ammount_of_subscribers": Subscribers, "channel_url": channel_url, 'daily': daily, 'weekly':weekly, 'monthly': monthly, 'total': total, 'last_updated': last_updated}
        insert_into_mongo(channel_info, 'tg_scrapers', 'channel_main_info', 'channel_username')
    except:
        daily = 0
        weekly = 0
        monthly = 0
        total = 0
        last_updated = datetime_to_string(datetime.now(pytz.utc))
        channel_info = {"channel_username": channel_username, "channel_name": Channel_Name, "channel_id": Channel_ID, "description": Description, "description_in_english": description_in_english, "urls_in_description": urls_in_description, "ammount_of_subscribers": Subscribers, "channel_url": channel_url, 'daily': daily, 'weekly':weekly, 'monthly': monthly, 'total': total, 'last_updated': last_updated}
        insert_into_mongo(channel_info, 'tg_scrapers', 'channel_main_info', 'channel_username')
    return Channel_Name, Channel_ID, channel_url

async def extract_message_media(message, media_dir, message_id, attachments):
    if message.media:
        media_items = [message.media]  # Assume it's a single item by default
        if hasattr(message.media, '__iter__'):
            media_items = message.media  # It's actually iterable (e.g., an album)

        for media in media_items:
            try:
                media_path = await client.download_media(media, file=media_dir)
                attachments.append(media_path)
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Delay between downloads
            except FloodWaitError as e:
                logger.error(f"Rate limit hit while downloading media. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                logger.error(f"Error downloading media from message {message_id}: {str(e)}")
                continue
    else:
        media_path = None
    return media_path

async def extract_message_info(message, count_of_messages):
    sender = await message.get_sender()
    sender_username = sender.username if sender else "Unknown" 
    try:
        sender_id = message.sender_id 
    except:
        sender_id = "Unknown" 
        logger.error("Unknown sender id")
    message_id = message.id 

    message_content = message.text 
    try:
        message_content_in_english = translate_to_english(str(message_content)) #
    except Exception as e:
        logger.error(f"failed to translate")
        logger.error(f"{e}")
        
        message_content_in_english = None 
    try: 
        urls_in_message = extract_urls_from_text(message_content) #
    except: 
        urls_in_message = None
    post_type = "post" 
    post_number = count_of_messages 
    attachments = []
    try:
        message_date = message.date.strftime('%Y-%m-%d %H:%M:%S')
    except:
        message_date = "No posted date found"

    message_views = message.views if message.views is not None else "N/A"
    
    return sender_username, sender_id, message_id, message_content, message_content_in_english, urls_in_message, post_type, post_number, attachments, message_date, message_views


async def extract_reply_media(reply, media_dir, message_id, reply_attachments):
    if reply.media:
        reply_media_items = [reply.media]  # Assume it's a single item by default
        if hasattr(reply.media, '__iter__'):
            reply_media_items = reply.media  # It's actually iterable (e.g., an album)

        for media in reply_media_items:
            try:
                reply_media_items = await client.download_media(media, file=media_dir)
                reply_attachments.append(reply_media_items)
                await asyncio.sleep(random.uniform(0.5, 1.5))  # Delay between downloads
            except FloodWaitError as e:
                logger.error(f"Rate limit hit while downloading media. Waiting for {e.seconds} seconds.")
                await asyncio.sleep(e.seconds)
                continue
            except Exception as e:
                logger.error(f"Error downloading media from message {message_id}: {str(e)}")
                continue
    else:
        reply_media_items = None

async def extract_reply_info(reply, reply_count):
    reply_sender = await reply.get_sender()
    reply_sender_username = reply_sender.username if reply_sender else "Unknown"
    try:
        reply_sender_id = reply.sender_id
    except:
        logger.error("reply sender not found")
        reply_sender_id = None
    try:
        reply_content = reply.text
    except:
        logger.error("reply content not found")
        reply_content = None
    try: 
        reply_content_in_english = translate_to_english(str(reply_content))
    except:
        logger.error(f"failed to translate")
        reply_content_in_english = None
    try:
        urls_in_reply_content = extract_urls_from_text(reply_content)
    except:
        urls_in_reply_content = None
    reply_post_type = "reply"
    reply_number = reply_count
    try:
        reply_date = reply.date.strftime('%Y-%m-%d %H:%M:%S')
    except:
        logger.error("Reply date not found")
        reply_date = None
    try:
        reply_id = reply.id
    except:
        logger.error("reply_id not found")
        reply_id = None
    return reply_sender_username, reply_sender_id, reply_content, reply_content_in_english, urls_in_reply_content, reply_post_type, reply_number, reply_date, reply_id

async def main(channel_usernames):
    async with client:
        download_media = config.get("download_media")
        crawl_first = config.get("channel_crawl_first")
        for channel_username in channel_usernames:
            # Fetching the channel
            channel = await client.get_entity(channel_username)
            message_counter = 1  # Counter to track the number of messages processed
            
            channel_details = await client(GetFullChannelRequest(channel_username))
            
            Channel_Name, Channel_ID, channel_url = extract_channel_details(channel_details, channel_username)

            # Create a directory for downloaded media
            media_dir = f"downloaded_media/{channel_username}"
            os.makedirs(media_dir, exist_ok=True)
            count_of_messages = 1
            sleep_time = random.randint(5, 10)
            # Iterate over all messages in the channel
            async for message in client.iter_messages(channel, limit=None, wait_time=sleep_time):
                try:
                    message_id = message.id #
                    message_content = message.text
                    if crawl_first == True:
                        try:
                            word_found = contains_any_word(message_content, word_list)
                            if word_found == False:
                                logger.error(f"No keyword found on message {message_id}, skipping...")
                                continue
                        except Exception as e:
                            logger.error(f"Error trying to crawl message {message_id}")
                            logger.error(f"{e}")
                            continue
                    
                        
                    sender_username, sender_id, message_id, message_content, message_content_in_english, urls_in_message, post_type, post_number, attachments, message_date, message_views = await extract_message_info(message, count_of_messages)
                    
                    # Check and download media from the main message
                    if download_media == True:                  
    
                        try:
                            attachments = await extract_message_media(message, media_dir, message_id, attachments)
                        except Exception as e:
                            logger.error(f"Failed to extract_message_media on message {message.id}")
                            logger.error(f"{e}")
                            attachments = []
                    else:
                        attachments = []
                    message_counter += 1
                    count_of_messages += 1
                    reply_count = 1
                    replies = []
                    replies_without_attach = []
                    # Check if the message has replies (comments)
                    if message.replies:
                        try:
                            # Fetching the replies (comments)
                            async for reply in client.iter_messages(channel, reply_to=message.id, limit=None, wait_time=sleep_time):
                                                        
                                reply_sender_username, reply_sender_id, reply_content, reply_content_in_english, urls_in_reply_content, reply_post_type, reply_number, reply_date, reply_id = await extract_reply_info(reply, reply_count)
                                                            
                                # Check and download media from the reply
                                if download_media == True:                              
                                    
                                    try:
                                        await extract_reply_media(reply, media_dir, message_id, reply_attachments)
                                    except Exception as e:
                                        logger.error(f"Failed to extract_reply_media on message {message.id}")
                                        logger.error(f"{e}")
                                        reply_attachments = []
                                else:
                                    reply_attachments = []
                                reply_count += 1
                            
                                reply_info = {"message_id": reply_id, "sender": reply_sender_username, "sender_id": reply_sender_id, "content": reply_content, "content_in_english": reply_content_in_english, "urls_in_content": urls_in_reply_content, "post_type": reply_post_type, "post_number": reply_number, "date_posted": reply_date}
                                replies_without_attach.append(reply_info)
                                reply_info_with_attach = {"message_id": reply_id, "sender": reply_sender_username, "sender_id": reply_sender_id, "content": reply_content, "content_in_english": reply_content_in_english, "urls_in_content": urls_in_reply_content, "post_type": reply_post_type, "post_number": reply_number, "date_posted": reply_date, "attachments": reply_attachments}
                                replies.append(reply_info_with_attach)
                                
                                
                        except Exception as e:
                            logger.error(f"Unable to fetch replies for message ID {message.id}")
                            logger.error(f"{e}")
                    message_info_without_attach = {"message_id": message_id, "sender": sender_username, "sender_id": sender_id, "content": message_content, "content_in_english": message_content_in_english, "urls_in_content": urls_in_message, "post_type": post_type, "post_number": post_number, "date_posted": message_date, "views": message_views, "replies": replies_without_attach}
                    hashed_message = hash_sha256(message_info_without_attach)
                    
                    existing_message_document = find_one_document('message_id', message_id, 'channels_messages', 'tg_scrapers')
                    if existing_message_document:
                        existing_document_hash = existing_message_document.get('hash')
                    else:
                        existing_document_hash = None
                    
                    if existing_document_hash == hashed_message:
                        logger.info(f"No changes to message {message_id}")
                        continue
                    
                    elif existing_document_hash != hashed_message and existing_message_document is not None:
                        logger.info(f"message_id: {message_id} existing_document_hash != hashed_message and existing_message_document is not None:")
                        existing_document_date_scraped = existing_message_document.get('date_scraped')
                        existing_document_unix_time = existing_message_document.get('date_scraped_unix')
                        current_datetime = datetime.now()
                        updated_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Truncate to 6 decimal places
                        updated_unix_time = current_datetime.timestamp()
                        channel_information = {"channel_username": channel_username, "channel_name": Channel_Name, "channel_id": Channel_ID, "channel_url": channel_url}
                        info_to_send_to_db = {"channel_information": channel_information, "message_id": message_id, "sender": sender_username, "sender_id": sender_id, "content": message_content, "content_in_english": message_content_in_english, "urls_in_content": urls_in_message, "post_type": post_type, "post_number": post_number, "date_posted": message_date, "views": message_views, "attachments": attachments, "replies": replies, "date_scraped":existing_document_date_scraped, "date_scraped_unix": existing_document_unix_time, 'updated_at':updated_datetime, 'updated_at_unix_time':updated_unix_time, "hash": hashed_message}
                        try:
                            insert_into_mongo(info_to_send_to_db, 'tg_scrapers', 'channels_messages', 'message_id')
                        except:
                            logger.error(f"Failed to insert data from message {message_id} to database")
                            continue
                        try:
                            logger.info("trying to update post count")
                            update_post_counts(1, 'channel_username', channel_username, 'channel_main_info', 'tg_scrapers')
                        except:
                            logger.error(f"Failed to update count on message {message_id}")
                        
                    else:
                        logger.info(f"message_id: {message_id} ELSE")
                        current_datetime = datetime.now()
                        formatted_datetime = current_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Truncate to 6 decimal places
                        unix_time = current_datetime.timestamp()
                        channel_information = {"channel_username": channel_username, "channel_name": Channel_Name, "channel_id": Channel_ID, "channel_url": channel_url}
                        info_to_send_to_db = {"channel_information": channel_information, "message_id": message_id, "sender": sender_username, "sender_id": sender_id, "content": message_content, "content_in_english": message_content_in_english, "urls_in_content": urls_in_message, "post_type": post_type, "post_number": post_number, "date_posted": message_date, "views": message_views, "attachments": attachments, "replies": replies, "date_scraped":formatted_datetime, "date_scraped_unix": unix_time, "hash": hashed_message}
                        try:
                            insert_into_mongo(info_to_send_to_db, 'tg_scrapers', 'channels_messages', 'message_id') 
                        except:
                            logger.error(f"Failed to insert data from message {message_id} to database")
                            continue
                        try:
                            logger.info("trying to update post count")
                            update_post_counts(1, 'channel_username', channel_username, 'channel_main_info', 'tg_scrapers')
                        except:
                            logger.error(f"Failed to update count on message {message_id}")
                            

                except FloodWaitError as e:
                    logger.error(f"Rate limit hit. Waiting for {e.seconds} seconds.")
                    await asyncio.sleep(e.seconds)  # Sleep for the duration of the rate limit
                    continue
                except Exception as e:
                    # Handle other exceptions that might occur
                    logger.error(f"An error occurred: {str(e)}")
                    continue

with client:
    client.loop.run_until_complete(main(channel_usernames))