# Setup

You should be to set this up by running:

1. just build
2. just up
3. just manage seed_test_user
4. just manage migrate

Most of the setup is the same except for I am using a prebuilt postrges image since the custom built one is missing. Some minor settings have changed as well (such as the authentication order, and adding a DB_URL to local_env). Most of these are documented in DeveloperNotes as I came across them.

## How to import csv

You have two options:

### Admin Panel

Go to the admin panel and upload the document through UploadTasks

### REST API

Go to the swagger UI on api/docs. Find the UploadTasks resource and upload through the POST resource.

It is also possible to use whatever HTTP tool but this is the easiest. You can fetch and auth token and use it through curl but it requires some edits to the Authorization Header to include Token.

`Authorization: Token <token>`

This does not show up in the swagger documentation since it is kind of nonstandard django thing.

## How to view status

You can view status by looking up the status in either the NctSearchTask model for each individual search or the UploadTask for the entire search. Both can be accessed through the REST API or the admin panel.
