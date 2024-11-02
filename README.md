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

With Docker, you don't need to install Python or dependencies directly on your host machine. Environment variables from the .env file will automatically configure the container.

## Usage

## Authors and acknowledgment

## License

