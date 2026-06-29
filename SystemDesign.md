## System Design

### Requirements

Hard requirements for the project

1. Process CSV file uploads and load the studies into the database.
2. CSV processing needs to be run outside the request cycle
3. Duplicate runs must be idempotent
4. Must handle errors on the processing side
5. Must display status in some way.

### Additional Notes

1. Durability. The celery broker is through redis. If it goes down jobs might be lost and the process may be stuck in limbo. Need a process to unstick these jobs.
2. Error handling. It is obvious to retry various 50x http errors. 400 is more difficult. For instance 404 may indicate an id does not exist, so it should be marked as complete.
3. Update study records. Due to the async nature of this process and how the CSV is processed the same study could appear in multiple tasks. Should this study be cached and reused or updated with latest version. It is hard to say. In this case I am going to keep them cached since I don't expect them to change.
4. Race conditions. Due to being async it is possible that two studies could be searched at once. This might require locking on the celery jobs by nct id. If the API calls were priced it might require locking on the the celery calls but that is not needed here. Duplicate lookups can update the record. It is important to only create one record for nct id.
5. Primary Keys. Instead of AutoInt for these new models I will use uuid for the PK to prevent enumeration attacks (even though risk is low for these endpoints).
6. Primary key for studies. A decision should be made if the nct id is sufficient for uniquely identifying the study. Currently I am putting a unique primary key as well as enforcing the nct id is unique. This is potentially more flexible in the future in case this model needs to be refactored.
7. Storing uploaded CSVs. Currently file uploads are stored in the media directory in django. This is sufficient for this task. It might be good to have a task to clean up the csv, but I think it is out of scope (it raises questions of should it be deleted? Do you need it for auditing?). For production I would recommend S3 for storage and cleanup to move it to cold storage.
8. Auth. Who can upload the file and who can view the data. Currently I am limiting to admin for simplicity.
9. Cleaning up data. If you want to delete a file upload it would be necessary to do some cleanup. I did the minimum by setting up cascade delete so all database models would be deleted. Pending jobs will fail if they are inflight. Studies are not deleted since they may be referenced by other file uploads.

### Approach

Overall approach is to provide an REST style API for models (the basic services can be reused for MVC as well to provide a display). The APIs will simply query the models through Django ORM. The only create endpoint through the API will be the csv upload endpoint. The REST apis will various parameters to filter including by upload id.

The admin portal will also be supported for submitting documents and viewing status.

There will be some simple validation such as checking if the CSV is valid and checking for duplicate CSVs on input.

As part of the POST to the file upload a celery task will be scheduled. This task will parse the CSV and generate some search tasks. These will be represented in the DB with a DB model connecting the File Upload to the Studies.

This task will async generate the jobs to do the lookups for each nct-id. This will decouple the jobs and prevent any one tasks from doing a large batch of work except for the initial csv import.

These async celery tasks will handle updating the Study Models as well as the search models. Each search is fully independent so any error will not block any others (they are on separate tasks). If a task failed with a known network issue it will go into retry. If it fails otherwise the task will fail and can be monitored in admin panel or flower to see the issue.

If a task fails with a 404 it will be marked as not found. A future lookup will retry it but the current Search.

To determine when a file upload is complete each NctSearchTask will have a status determining if it is completed. A separate task is run periodically to correlate these and update the UploadTask status when all are in a complete state (ie. not processing.)

A rough overview is in the diagram below (subject to change during implementation):
![alt](./System%20Design.drawio.png)

### Architecture

I am implementing all logic into django services. This will be independent from views/celery tasks and allow easy testing in unit tests and simplify integration testing by only testing at the integration point (ie. does the DB persist, does web APIs).

These services will be found in tp_backend_test/studies/services.

These are all classed based with dependencies injected as arguments when needed (usually DB managers, but also interfaces to call tasks or other clearly separate components such as making API calls). When ever a dependency needs to be injected I define an interface using protocols that it must meet. This allows the python type system to enforce the concrete implementations meet the spec. Though the type hinting is limited due to Django magic that is used in places.

### DB Schema

I separated the DB schema into 3 tables. One Table for the various jobs to fetch the study data, and one for the studies themselves.

The UploadTask table gets generated on POST to the backend. It contains timestamps, id, a file hash and file ref. The file hash is used to dedupe files so duplicate files are not processed twice (since they can be large.) There needs to be an index on the hash since it is queried to do the deduplication step.

The NctSearchTask will handle the status of the searches. The relate back to the UploadTask and Study. This architecture will allow multiple file uploads to manage all the nct ids in their upload but still associate it back to a single Study record, preventing duplication. This also allows cleanup if the UploadTask is deleted it can clean up its search jobs using cascade (although only admin can do that and it is not strictly a supported operation).

Study will simply be a model storing data. The requirements where light so I kept it basic but can easily be expanded by editing the parsing in the service definition + the db model.

### Testing

Due to architecting the code to use services with dependency injection it is easy to mock components in tests. Most tests thus use Unit testing with mocks for convenience. Some are more convenient to test with actual db models and done that way.

In actual production system I would take more care to separate and flesh out both tests as they both serve a purpose, but for this I kept it simple.

### Improvements for the future

1. Better Organization: I stuck everything in studies/services for now. Some components might be reused over several apps and should go into common.
2. More consistent testing. I mostly used Claude to generate tests and review it. It resulted in a mix of integration and unit tests. I would like to improve this to be more consistent. I generally prefer a strict separation of unit tests and integration tests.
3. Figure out better dependency injection. I made simple factories relating to the service for simplicity. For celery in particular it was difficult because of how tasks need to be defined (generally a static method or a function). I would like to explore better ways than the semi hardcoding I have now (either a DI framework or some other clever approach).
4. Better indexing. I added basic indexes where it seemed obvious. It would be good to measure performance and determine more targeted optimizations.
5. Scaling celery. The full csv is slow due to the large amount of tasks that need to be done. The nature of python being single threaded limits it to an extent. I added auto scaling that helped but horizontal scaling may be needed in production.
