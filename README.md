# TeleCatch

![alt text](teledash/static/img/logo/logo_color_bg.jpeg)



TeleCatch is a comprehensive web application that provides a web-based interface and a REST api for managing and analyzing [Telegram](https://telegram.org/) data.
With a secure and user-friendly dashboard, users can manage Telegram accounts, configure data collections, and access insightful visualizations directly from their browser.

It is based on [Telethon](https://github.com/LonamiWebs/Telethon), to interact with Telegram APIs, and [FastAPI](https://github.com/fastapi/fastapi) for API and UI development.

TeleCatch has the following key features:
- management of custom collection of Telegram groups and channels
- management of multiple Telegram accounts
- download of messages and/or images from Telegram directly to local clients (streaming, no need to store data on the server first)
- quick visualization of samples



## Installation

### Local deployment
To install and set up TeleCatch, follow the steps below. This project requires Python 3.10 or above, environment variables for configuration, and optionally, Docker for containerized deployment.

1. Clone the Repository
First, clone the repository locally:

``` bash
git clone https://github.com/labaffa/telecatch.git
cd telecatch
```

2. Install Dependencies

From inside repo folder, via pip:

``` bash
pip install -r requirements.txt
```

3. Set Up Environment Variables
TeleCatch requires several environment variables to configure encryption and email functionality. You can add these variables in a .env file in the project root.

Required Variables:

```env
JWT_SECRET_KE: Hex key (32-bit) used for jwt signature.
JWT_REFRESH_SECRET_KE: Hex key (32-bit) for refresh jwt signature.
DATA_SECRET_KEY: Hex key (16-bit) for user data encryption
MAIL_USERNAME: The email address for sending verification and reset emails.
MAIL_PASSWORD: Password for the email account.
```

To create a 32-bit and a 16-bit hex key, you can use the openssl command to generate random data:

- 32-bit hex key (for JWT_SECRET_KEY and JWT_REFRESH_SECRET_KEY):
  ```bash
  openssl rand -hex 32  # Generates a 64-character hex key (32 bytes)
  ```
- 16-bit hex key (for DATA_SECRET_KEY):
  ```bash
  openssl rand -hex 16  # Generates a 32-character hex key (16 bytes)
  ```
4. Run Database Migrations
Before starting the server, ensure the database schema is up-to-date by running Alembic migrations:

```bash
alembic upgrade head
```

5. Run TeleCatch
Start the server by running:

```bash
uvicorn telecatch.main:app
```

The app will be accessible at `http://127.0.0.1:8000`.

### Using Docker
If you prefer to run TeleCatch in a Docker container, follow these steps with [docker installed](https://docs.docker.com/engine/install/) :

Build the Docker image:


```bash

docker build -t telecatch .
```


Create a `.env` file containing all the required variables above mentioned and run the Docker container:


```bash
docker run --env-file .env -p 8000:8000 telecatch
```


With the previous command, app's data (users, Telegram clients info, metadata, etc.) stay at *container's level*, which means that any new `docker run` loses track of all the data.  
To make data persistent across different *containers*, a local folder of the host machine can be [mounted](https://docs.docker.com/engine/storage/bind-mounts/). 

The new command will be then:
```bash
docker run --env-file .env --mount type=bind,source=/absolute/host/path/for/app/data,target=/app/teledash/sessions -p 8000:8000 telecatch
```
The app will be accessible at `http://0.0.0.0:8000`.


## Usage

### Web interface

The web interface allows users to manage and query their Telegram data through a user-friendly dashboard. Here’s a step-by-step guide on how to get started:
1. Registration and Login

   - When first using TeleCatch on your browser, you will be redirected to `http://127.0.0.1:8000/app_login`
   - Go to `Sign Up` tab and fill in the registration form with a valid email, username and password.
   - If the message for a correct registration is shown, move to `Log In` tab and log in with your credentials.

2. Telegram Authentication
   
   - The authentication process can be done from the `http://127.0.0.1:8000/clients` view, or clicking `Client phone` from the navbar on top.
   - Before being able to authenticate and create a Telegram client, you must have or get your own api_id and api_hash following [Telegram instructions](https://my.telegram.org).
   - After you click on "Register account", wait for a code Telegram will send on your app and insert it. Authentication should be complete.
   - IMPORTANT: disable 2factor authentication from your Telegram app's settings before authentication.

3. Create a collection of groups and channels
   - go to `http://127.0.0.1:8000/clients` or click  `Active collection` on the navbar
   - click `Choose file` to upload a csv-like file (.xls, .xlsx, .csv, .tsv) containing the identifiers of the groups and channels of the new collection. A mandatory `url` column must be present: this is the place for urls and/or usernames of groups and channels. Other optional columns are considered: language, location, category
   - upload the file, choose a title for the collection and save it.
  
4. Querying Data:
   - go to the home `http://127.0.0.1:8000/` or click `Home` on the navbar. Use the search bar to query messages within your collections
   - you can filter by dates, group or channel, type of data access (show a sample on the `Results` table or export and download all the messages and images to a tsv file)


## Authors and acknowledgment


TeleCatch was developed with support from the CGIAR [Initiative on Fragility, Conflict, and Migration](https://www.cgiar.org/initiative/fragility-conflict-and-migration/) and the CGIAR [Initiative on Climate Resilience, ClimBeR](https://www.cgiar.org/initiative/climate-resilience/). We would like to thank all funders who supported this research through their contributions to the [CGIAR Trust Fund](https://www.cgiar.org/funders/).



## License

