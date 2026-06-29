import chardet


class NctIdCsvValidatorService:
    """Implementation of the csv validator protocol."""

    def validate(self, data: bytes) -> bool:
        """Takes bytes and returns if it is a valid csv."""
        try:
            encoding = chardet.detect(data)["encoding"] or "utf-8"
            first_line = data.split(b"\n")[0].decode(encoding, errors="replace")
        except UnicodeDecodeError:
            return False
        else:
            return "NCT Number" in first_line
