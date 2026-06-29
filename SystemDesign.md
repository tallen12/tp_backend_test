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
4. Race conditions. Due to being async it is possible that two studies could be searched at once. This might require locking on the celery jobs by nct id. This is probably the approach I am doing if it doesn't turn out too complicated. Since this is a dummy api and not priced I don't think it matters too much if duplicates are run.
5. Primary Keys. Instead of AutoInt for these new models I will use uuid for the PK to prevent enumeration attacks (even though risk is low for these endpoints).
6. Primary key for studies. A decision should be made if the nct id is sufficient for uniquely identifying the study. Currently I am putting a unique primary key as well as enforcing the nct id is unique. This is potentially more flexible in the future in case this model needs to be refactored.
7. Storing uploaded CSVs. Currently file uploads are stored in the media directory in django. This is sufficient for this task. It might be good to have a task to clean up the csv, but I think it is out of scope (it raises questions of should it be deleted? Do you need it for auditing?). For production I would recommend S3 for storage and cleanup to move it to cold storage.
8. Auth. Who can upload the file and who can view the data. Currently I am limiting to admin for simplicity.

### Approach

Overall approach is to provide an REST style API for models (the basic services can be reused for MVC as well to provide a display). The APIs will simply query the models through Django ORM. The only create endpoint through the API will be the csv upload endpoint.

The admin portal will also be supported for submitting documents and viewing status.

As part of the POST to the file upload a celery task will be scheduled. This task will async generate the jobs to do the lookups. These async celery tasks will handle updating the models.

A rough overview is in the diagram below (subject to change during implementation):
![alt](./System%20Design.drawio.png)

### Architecture

I am implementing all logic into django services. This will be independent from views/celery tasks and allow easy testing in unit tests and simplify integration testing by only testing at the integration point (ie. does the DB persist, does web APIs).

These services will be found in tp_backend_test/studies/services
