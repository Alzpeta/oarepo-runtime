#
# This package was taken from Invenio vocabularies and modified to be more universal
#
import abc
import dataclasses
import itertools
import logging
from typing import List

from .errors import TransformerError, WriterError

log = logging.getLogger("datastreams")
from invenio_access.permissions import system_identity


class StreamEntry:
    """Object to encapsulate streams processing."""

    def __init__(self, entry, filtered=False, errors=None, context=None):
        """Constructor."""
        self.entry = entry
        self.filtered = filtered
        self.errors = errors or []
        self.context = context or {}

    @property
    def ok(self):
        return not self.filtered and not self.errors


@dataclasses.dataclass
class DataStreamResult:
    ok_count: int
    failed_count: int
    skipped_count: int
    failed_entries: List[StreamEntry]


def noop(*args, **kwargs):
    """Noop callback"""


class AbstractDataStream(abc.ABC):
    def __init__(
        self,
        *,
        readers,
        writers,
        transformers=None,
        success_callback=None,
        error_callback=None,
        progress_callback=None,
        **kwargs,
    ):
        """Constructor.
        :param readers: an ordered list of readers (whatever a reader is).
        :param writers: an ordered list of writers (whatever a writer is).
        :param transformers: an ordered list of transformers to apply (whatever a transformer is).
        """
        self._readers = readers
        self._transformers = transformers
        self._writers = writers
        self._error_callback = error_callback or noop
        self._success_callback = success_callback or noop
        self._progress_callback = progress_callback or noop

    @abc.abstractmethod
    def process(self, max_failures=100) -> DataStreamResult:
        pass


class DataStream(AbstractDataStream):
    """Data stream."""

    def process(self, max_failures=100) -> DataStreamResult:
        """Iterates over the entries.
        Uses the reader to get the raw entries and transforms them.
        It will iterate over the `StreamEntry` objects returned by
        the reader, apply the transformations and yield the result of
        writing it.
        """
        _written, _filtered, _failed = 0, 0, 0
        failed_entries = []
        read_count = 0

        for stream_entry in self.read():
            read_count += 1
            self._success_callback(read=read_count, written=_written, failed=_failed)
            if stream_entry.errors:
                if len(failed_entries) < max_failures:
                    _failed += 1
                    failed_entries.append(stream_entry)
                continue

            transformed_entry = self.transform_single(stream_entry)
            if transformed_entry.errors:
                _failed += 1
                failed_entries.append(transformed_entry)
                continue
            if transformed_entry.filtered:
                _filtered += 1
                continue

            written_entry = self.write(transformed_entry)
            if written_entry.errors:
                self._error_callback(written_entry)
            else:
                self._success_callback(written_entry)
            _written += 1

        return DataStreamResult(
            ok_count=_written,
            failed_count=_failed,
            skipped_count=_filtered,
            failed_entries=failed_entries,
        )

    def read(self):
        """Read the entries."""
        for rec in itertools.chain(*[iter(x) for x in self._readers]):
            yield rec

    def transform_single(self, stream_entry, *args, **kwargs):
        """Apply the transformations to an stream_entry."""
        for transformer in self._transformers:
            try:
                stream_entry = transformer.apply(stream_entry)
            except TransformerError as err:
                stream_entry.errors.append(
                    f"{transformer.__class__.__name__}: {str(err)}"
                )
                return stream_entry  # break loop

        return stream_entry

    def write(self, stream_entry, *args, **kwargs):
        """Apply the transformations to an stream_entry."""
        for writer in self._writers:
            try:
                writer.write(stream_entry)
            except WriterError as err:
                log.error("Error in writer: ", err, repr(stream_entry.entry))
                stream_entry.errors.append(f"{writer.__class__.__name__}: {str(err)}")
            except Exception as err:
                log.error("Unexpected error in writer: ", err, repr(stream_entry.entry))
                stream_entry.errors.append(f"{writer.__class__.__name__}: {str(err)}")

        return stream_entry

    @property
    def read_entries(self):
        """The total of entries obtained from the origin."""
        return self._read

    @property
    def written_entries(self):
        """The total of entries written to destination."""
        return self._written

    @property
    def filtered_entries(self):
        """The total of entries filtered out."""
        return self._filtered
