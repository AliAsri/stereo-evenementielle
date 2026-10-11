"""Reuse the four HDF5 dataset handles while retaining all indexed-reader checks."""
from .dsec_indexed import IndexedDSECReader


class CachedIndexedDSECReader(IndexedDSECReader):
    """One handle per field keeps HDF5 chunk caches alive across adjacent windows.

    No events are prefetched by application code. HDF5 may decompress whole
    chunks internally, as in the reference; only exact causal slices are returned.
    Dataset cache limits are inherited from HDF5 and exposed for provenance.
    """
    def __enter__(self):
        super().__enter__()
        try:
            group = self.events
            self.events = {key: group[key] for key in ('x', 'y', 't', 'p')}
            self.cache_bytes = {key: dataset.id.get_access_plist().get_chunk_cache()[1]
                                for key, dataset in self.events.items()}
        except Exception:
            super().__exit__()
            raise
        return self

    def __exit__(self, *args):
        try:
            super().__exit__(*args)
        finally:
            self.events = None
