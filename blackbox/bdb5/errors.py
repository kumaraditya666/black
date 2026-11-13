class BDB5Error(Exception):
    """Base class for deterministic BDB-5 harness errors."""


class BlockedCaseError(BDB5Error):
    """The case is not approved for evaluation or is not a synthetic dry-run case."""


class ManifestValidationError(BDB5Error):
    """A manifest cannot be used by this harness."""


class PacketValidationError(BDB5Error):
    """The model-visible packet violates a hard separation rule."""


class UnsupportedModeError(BDB5Error):
    """Only SYNTHETIC_DRY_RUN is implemented."""
