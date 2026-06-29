from io import BytesIO

from django.core.files.uploadedfile import InMemoryUploadedFile


def make_uploaded_file(
    content: bytes = b"NCT Number\nNCT06596772\nNCT05660161\nNCT07641023",
) -> InMemoryUploadedFile:
    """Generate a mock django uploaded file."""
    return InMemoryUploadedFile(
        file=BytesIO(content),
        field_name="source_file",
        name="test.csv",
        content_type="text/csv",
        size=len(content),
        charset=None,
    )
