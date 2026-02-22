
class Transport:
    """Base transport interface."""

    def set_write_mode(self):
        """Set transport to write mode (if supported)."""
        pass

    def set_read_mode(self):
        """Set transport to read mode (if supported)."""
        pass

    def write(self, data):
        raise NotImplementedError()

    def read(self, size=1):
        raise NotImplementedError()

    def init(self, **kwargs):
        """Reconfigure transport (if supported)."""
        pass

    def cleanup(self):
        """Cleanup resources (if supported)."""
        pass


