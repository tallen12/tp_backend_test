import logging
from typing import TYPE_CHECKING
from typing import Any
from typing import Protocol
from typing import cast

import requests
from requests import codes

from tp_backend_test.studies.models import NctSearchTask
from tp_backend_test.studies.models import Study

if TYPE_CHECKING:
    from collections.abc import MutableMapping

    from rest_framework.compat import QuerySet

LOGGER = logging.getLogger(__name__)


class StudyFetcherError(Exception):
    """Base exception for all StudyFetcher errors."""

    def __init__(self, nct_id: str, message: str):
        self.nct_id = nct_id
        super().__init__(f"[{nct_id}] {message}")


class StudyNotFoundError(StudyFetcherError):
    """Raised on 404 — study does not exist in the API. Do not retry."""

    def __init__(self, nct_id: str):
        super().__init__(nct_id, "Study not found")


class StudyServerError(StudyFetcherError):
    """Raised on 5xx — transient server failure. Safe to retry."""

    def __init__(self, nct_id: str, status_code: int):
        self.status_code = status_code
        super().__init__(nct_id, f"Server error ({status_code})")


class StudyTimeoutError(StudyFetcherError):
    """Raised on read timeout. Retry with exponential backoff."""

    def __init__(self, nct_id: str):
        super().__init__(nct_id, "Request timed out")


class StudyFetcher:
    def __init__(self, ct_gov_url: str):
        self.ct_gov_url = ct_gov_url

    def fetch_data(self, nct_id: str):
        try:
            url = f"{self.ct_gov_url}/api/v2/studies/{nct_id}"
            resp = requests.get(url, timeout=5)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as e:
            raise StudyTimeoutError(nct_id) from e
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response is not None else None
            if status is not None:
                if status == codes.not_found:
                    raise StudyNotFoundError(nct_id) from e
                if status >= cast("int", codes.internal_server_error):
                    raise StudyServerError(nct_id, status) from e
            raise


class StudyModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager for Study."""

    def update_or_create(
        self,
        defaults: MutableMapping[str, Any] | None = ...,
        **kwargs: Any,
    ) -> tuple[Study, bool]: ...
    def filter(self, nct_id: str) -> QuerySet[Study]: ...
    def first(self) -> Study | None: ...


class NctSearchTaskModelManagerProtocol(Protocol):
    """Minimal subset of a Django model manager.

    Allows for easy mocking during unit tests (without the DB).
    """

    def filter(self, nct_id: str) -> QuerySet[NctSearchTask]: ...
    def update(
        self,
        **kwargs: Any,
    ) -> int: ...


class ProcessNctIdService:
    @staticmethod
    def factory(ct_gov_url: str, max_retries: int = 5):
        return ProcessNctIdService(
            study_fetcher=StudyFetcher(ct_gov_url),
            study_manager=Study.objects,
            nct_search_manager=NctSearchTask.objects,
            max_retries=max_retries,
        )

    def __init__(
        self,
        study_fetcher: StudyFetcher,
        study_manager: StudyModelManagerProtocol,
        nct_search_manager: NctSearchTaskModelManagerProtocol,
        max_retries: int = 5,
    ):
        self.study_fetcher = study_fetcher
        self.max_retries = max_retries
        self.study_manager = study_manager
        self.nct_search_manager = nct_search_manager

    def parse_data(self, json_data: dict[str, Any]) -> dict:
        protocol = json_data.get("protocolSection", {})
        return {
            "nct_id": protocol.get("identificationModule", {}).get("nctId", ""),
            "brief_title": protocol.get("identificationModule", {}).get(
                "briefTitle",
                "",
            ),
            "official_title": protocol.get("identificationModule", {}).get(
                "officialTitle",
                "",
            ),
            "overall_status": protocol.get("statusModule", {}).get("overallStatus", ""),
            "conditions": protocol.get("conditionsModule", {}).get("conditions", []),
            "study_type": protocol.get("designModule", {}).get("studyType", ""),
            "brief_summary": protocol.get("descriptionModule", {}).get(
                "briefSummary",
                "",
            ),
            "sponsor_primary_key": protocol.get("sponsorCollaboratorsModule", {})
            .get("leadSponsor", {})
            .get("name", ""),
        }

    def process_nct_id(self, nct_id: str, retries: int = 0):
        existing = self.study_manager.filter(nct_id=nct_id).first()
        new_status = None
        try:
            if not existing:
                data = self.study_fetcher.fetch_data(nct_id=nct_id)
                parsed_data = self.parse_data(data)
                existing, _ = self.study_manager.update_or_create(
                    nct_id=nct_id,
                    defaults=parsed_data,
                )
        except StudyNotFoundError:
            new_status = NctSearchTask.Status.NOT_FOUND
        except StudyFetcherError:
            if retries >= self.max_retries:
                new_status = NctSearchTask.Status.FAILURE
                return
            raise
        except Exception:
            new_status = NctSearchTask.Status.FAILURE
            LOGGER.exception("Unknown Error")
            raise
        finally:
            new_status = new_status or (
                NctSearchTask.Status.DONE
                if existing
                else NctSearchTask.Status.PROCESSING
            )
            self.nct_search_manager.filter(nct_id=nct_id).update(
                status=new_status,
                study_id=existing.id if existing else None,
            )
