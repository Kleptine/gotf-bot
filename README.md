# gotf-bot

A slack bot that hosts the game of the fortnight polls.

- when deploying, make sure to first download the GCP credential json file to the local directory.
- Copy the secret and token from the slack app information page.  
- when deploying use the command:
`gcloud functions deploy gotf --runtime python38 --trigger-http --allow-unauthenticated --set-env-vars "SLACK_SECRET=<secret>,SLACK_TOKEN=<token>"`
