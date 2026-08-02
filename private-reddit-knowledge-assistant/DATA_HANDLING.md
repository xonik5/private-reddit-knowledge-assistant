# Data handling and retention

## Collection boundaries

The application processes only a public Reddit post URL manually selected by an
authorized household user. It does not perform subreddit-wide collection,
background crawling, user enumeration, or user profiling.

For a submitted URL, the application requests only:

- the public submission title and body;
- the subreddit and canonical permalink;
- a bounded number of relevant public comments;
- minimal technical metadata needed for ordering and deletion checks.

Reddit usernames are removed before content is sent to the local analysis model
and are not part of the persistent knowledge note.

## Local processing

Processing takes place on a private home computer. Reddit content is not sent to
a hosted language-model provider. The local model performs inference and
summarization only. Reddit content is not used for training, fine-tuning,
benchmarking, or evaluation datasets.

## Retention

- Raw post and comment content is retained only for processing and compliance
  checks and is deleted no later than 48 hours after retrieval.
- Persistent private notes contain a summary, classification, key points, and a
  link to the original source rather than an archival copy of the discussion.
- Stored Reddit sources are periodically revalidated.
- If a post or comment is deleted, removed, protected, withheld, or otherwise no
  longer available, related Reddit-derived data is deleted or updated as
  required.
- If API access is terminated, cached Reddit content is deleted and further API
  access stops.

## Access and disclosure

The application is available only to two authorized members of one household.
It does not publicly display, sell, license, share, or otherwise distribute
Reddit data or derived notes.

## Security

OAuth credentials are stored outside source control in local environment
variables. Logs must not contain access tokens, client secrets, full API
responses, or raw post/comment bodies.

