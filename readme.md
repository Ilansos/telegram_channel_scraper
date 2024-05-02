# Telegram Channel Scraper Setup Guide

This guide provides instructions on how to set up and use the Telegram scraper script which collects data from Telegram channels.

## Overview

The Telegram Channel Scraper is a Python-based tool that extracts information from specified Telegram channels and stores it in a MongoDB database. It collects details about the channels, including:

    Channel Details: Name, ID, description, URLs in the description, and subscriber count.
    Messages: Information about each message, including the sender's ID and username, content, URLs in the content, replies, and any attached media.
    Replies: Information about replies to messages, including the sender's ID and username, content, URLs in the content, and attached media.

The scraper also provides options to download media files attached to messages and replies.


## Prerequisites

    Python 3.6 or higher
    MongoDB server

## Installation Steps
### 1. Clone the Repository

First, clone this repository to your local machine using git:

```bash
git clone https://github.com/Ilansos/telegram_channel_scraper.git
cd <repository-directory>
```

### 2. Install Python Dependencies

Install the required Python packages using pip:

```bash
pip install -r requirements.txt
```

### 3. Set Up MongoDB

Ensure that MongoDB is installed and running on your system. By default, the scraper connects to MongoDB at mongodb://localhost:27017/. If your MongoDB setup differs, adjust the connection string that is located on the config.json file on the root directory of the project.

### 4. Obtain Telegram API ID and Hash

To use the Telegram API, you need an API ID and hash. Follow these steps to obtain them:

    Log in to Telegram:
    Go to the Telegram API Development Tools website.

    Register your application:
    Once logged in, select 'API development tools' and fill out the form to register your new application. You will need to provide the application name, a short description, and the application platform.

    Get your API ID and hash:
    After submitting the form, you will receive your api_id and api_hash. Note these down as you will need to enter them in your config.json file.

### 5. Configure the Scraper

Modify the config.json file that is located in the root directory the project with the following configuration parameters:

```bash
{
  "telegram_api_id": "YOUR_API_ID",
  "telegram_api_hash": "YOUR_API_HASH",
  "mongo_uri": "mongodb://localhost:27017/",
  "download_media": true,
  "channel_crawl_first": true
}
```
telegram_api_id: Your Telegram API ID.

telegram_api_hash: Your Telegram API hash.

mongo_uri: If your MongoDB setup differs, adjust the connection string as needed.

download_media: Set to true if you want to download media from messages.

channel_crawl_first: Set to true to only process the first message of each channel.

### 6. Install Translation Languages

Run the translator_install.py script to install the necessary languages for the translation library:

```bash
python translator_install.py
```

This script downloads and installs translation packages needed to convert content to English from various languages.

### 7. Usage Details

The script telegram_scraper.py reads the channel usernames and keywords from channel_list.txt and keywords.txt, respectively. Ensure that these files are formatted as one entry per line.

### 8. Running the Scraper

To run the Telegram scraper, use the following command:

```bash
python telegram_channel_scraper.py
```

Make sure that all configuration files such as keywords.txt, channel_list.txt, and config.json are correctly set up and present in the directory from which you run the script.


### 9. Database Structure

The scraper stores data in a MongoDB database, organized as follows:

    Database Name: tg_scrapers

    Collections:

        channel_main_info: Contains documents representing each Telegram channel, with fields such as:
            channel_username
            channel_name
            channel_id
            description
            description_in_english
            urls_in_description
            amount_of_subscribers
            channel_url
            daily, weekly, monthly, total counts of posts
            last_updated

        channels_messages: Contains documents representing each message, with fields such as:
            channel_information (including channel username, name, ID, and URL)
            message_id
            sender and sender_id
            content and content_in_english
            urls_in_content
            post_type
            post_number
            date_posted and views
            attachments
            replies (list of reply documents)
            date_scraped and date_scraped_unix_time
            hash

## Logging System

The scraper uses Python's logging module to log various events such as errors, warnings, and informational messages throughout its execution. Here’s how the logging is set up:

    Configuration: Logging is configured to output messages to both the console and a file named telegram_scraper.log.
    Levels: The logging level is set to DEBUG, which means all levels of logs (debug, info, warning, error, critical) will be captured.
    Format: Each log message contains the timestamp, logger name, level of severity, and the message content.
    File Logging: Logs are appended to the file, allowing for persistent storage of log data across multiple runs of the scraper.

To view the logs, you can open the telegram_scraper.log file in any text editor or tail it in a console window:

```bash
tail -f telegram_scraper.log
```

This can be especially helpful for debugging issues or monitoring the scraper's progress.

## Support

For any issues or questions regarding the setup or operation of the scraper, please raise an issue in the repository or contact the repository maintainers.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

### MIT License