# Carrier Portal Authentication Flow

This document outlines the authentication process for the Carrier Portal, which uses Salesforce as an identity provider via the OAuth 2.0 protocol. It also explains how to configure the application using environment variables.

## 1. Local Configuration Setup

Before running the application, you must set up your local configuration. This application uses a `.env` file to manage environment variables for local development.

1.  **Create a `.env` file:** In the root directory of the project, make a copy of the `.env.example` file and name it `.env`.
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file:** Open the newly created `.env` file in a text editor. It contains all the necessary variables to run the application.

3.  **Update the values:** You will need to provide your own values for the Salesforce and other credentials. The file contains the default development credentials, but you should replace them with your own, especially the `SALESFORCE_CLIENT_ID` and `SALESFORCE_CLIENT_SECRET` from your own Salesforce Connected App.
    - **`SECRET_KEY`**: For security, you should generate a new secret key. You can do this by running the following command in your terminal:
      ```bash
      python -c 'import secrets; print(secrets.token_hex(24))'
      ```
    - **`SALESFORCE_REDIRECT_URI`**: Ensure this URI exactly matches the "Callback URL" you have configured in your Salesforce Connected App. For local development, this is typically `http://localhost:5000/auth/callback`.

**IMPORTANT:** The `.env` file contains sensitive credentials. It is listed in the `.gitignore` file and **must not** be committed to version control.

## 2. Authentication Process (OAuth 2.0 Flow)

The application authenticates users by delegating the login process to Salesforce. Here is a step-by-step breakdown of the flow:

1.  **User Navigates to Login:** The user accesses the `/login` page of the application.

2.  **Redirect to Salesforce:** The application does not show a traditional password form. Instead, it constructs a unique authorization URL and presents the user with a "Login with Salesforce" button.
    - *Code Reference:* `app/routes/auth.py` (the `login` function) and `app/services/salesforce_service.py` (the `get_oauth_url` function).

3.  **User Authenticates with Salesforce:** The user clicks the login button and is redirected to the Salesforce login page. They enter their Salesforce username and password.

4.  **User Grants Consent:** After logging in, Salesforce presents the user with a consent screen, asking them to grant the Carrier Portal application access to their basic information (as defined by the `scope` in the OAuth settings).

5.  **Salesforce Redirects to Callback URL:** Once the user grants consent, Salesforce redirects them back to the application using the `SALESFORCE_REDIRECT_URI` that was provided. This redirect includes a temporary `authorization_code`.

6.  **Application Exchanges Code for Tokens:** The application's backend receives the request at the `/callback` endpoint. It takes the `authorization_code` and sends it back to Salesforce in a secure, server-to-server request.
    - *Code Reference:* `app/routes/auth.py` (the `oauth_callback` function) and `app/services/salesforce_service.py` (the `exchange_code_for_token` function).

7.  **User Information is Fetched:** If the code exchange is successful, Salesforce returns an `access_token` and a `refresh_token`. The application then uses this `access_token` to request the user's identity information from Salesforce (e.g., user ID, name, email).

8.  **Session Creation:** The application verifies the user's carrier information, creates a user record in its own database (if one doesn't exist), and then creates a local session for the user using Flask-Login.

9.  **User is Logged In:** The user is now authenticated and redirected to the application's dashboard. Their session is managed by an encrypted cookie stored in their browser.

## 3. Logout Process

1.  **User clicks Logout:** The user clicks the logout link.
2.  **Session is Cleared:** The application clears the user's session data, invalidating the session cookie.
3.  **Revoke Salesforce Token (Optional):** For enhanced security, the application could also revoke the Salesforce access token, but this is not currently implemented.
4.  **User is Redirected:** The user is redirected back to the login page.
    - *Code Reference:* `app/routes/auth.py` (the `logout` function).
