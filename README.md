# Private Reddit Knowledge Assistant

This repository contains the Reddit-facing, read-only component of a private,
non-commercial knowledge-management application for two members of one
household.

The application is currently **paused pending explicit Reddit Data API
approval**. The code will not access Reddit without OAuth credentials supplied
after approval.

## Purpose

An authorized user manually sends one public Reddit post URL to a private
Telegram bot. The self-hosted application retrieves that single post and a
limited number of relevant comments, then sends a privacy-reduced text document
to a language model hosted on the user's home computer. The model creates a
private summary, category, key points, and source link.

The application:

- serves two authorized household users only;
- is private, self-hosted, and non-commercial;
- uses read-only OAuth access;
- does not crawl or continuously monitor subreddits;
- does not enumerate or profile Reddit users;
- does not post, comment, vote, report, moderate, or send messages;
- does not display advertising or sell, license, or redistribute Reddit data;
- does not use Reddit content for training, fine-tuning, or evaluation datasets;
- normally processes fewer than 20 manually submitted URLs per day.

## Data flow

1. An authorized user manually submits a specific Reddit URL.
2. A private queue forwards that URL to a worker on the home computer.
3. This module validates the URL and requests one submission through Reddit
   OAuth.
4. The module selects no more than the configured number of comments and removes
   usernames before creating the analysis document.
5. A local language model performs inference only; no Reddit content is sent to
   a hosted AI provider.
6. Raw Reddit content is deleted within 48 hours.
7. Saved sources are periodically revalidated. Reddit-derived data is removed if
   the source has been deleted or removed.

## API use

The client uses the OAuth client-credentials flow and sends a unique,
descriptive User-Agent. It requests only an individually submitted public post
and its bounded comment tree.

Example User-Agent format:

```text
windows:private-reddit-knowledge-assistant:v0.1.0 (by /u/REDDIT_USERNAME)
```

OAuth secrets are loaded only from environment variables and must never be
committed. See [`.env.example`](.env.example).

## Local development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .[dev]
python -m unittest discover -s tests -v
```

The test suite uses only the Python standard-library test runner, synthetic
fixtures, and an in-memory HTTP transport. It performs no network calls.

## Repository scope

This public repository intentionally contains only the Reddit access component,
tests, and compliance documentation. Private Telegram configuration, database
credentials, server addresses, household data, saved notes, and local model
configuration are excluded.

See [DATA_HANDLING.md](DATA_HANDLING.md) and [SECURITY.md](SECURITY.md).
