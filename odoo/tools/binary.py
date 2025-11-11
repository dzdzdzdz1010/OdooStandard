import base64
import io
import os
from collections.abc import Buffer

from .misc import file_open

__all__ = ['BinaryValue']


class BinaryValue(Buffer):
    """Lazy representation of bytes."""

    __slots__ = ()

    def open(self) -> io.IOBase:
        """Open the file for reading."""
        return io.BytesIO(self.content)

    @property
    def content(self) -> bytes:
        """The ``bytes``."""
        raise NotImplementedError

    @property
    def mimetype(self) -> str:
        """Guessed mimetype."""
        from .mimetypes import guess_mimetype  # noqa: PLC0415
        return guess_mimetype(self.content, '')

    @property
    def size(self) -> int:
        """Length of the binary."""
        return len(self.content)

    def __bytes__(self):
        # shortcut for `bytes(...)`
        return self.content

    def __buffer__(self, flags: int) -> memoryview:
        # https://peps.python.org/pep-0688/
        return memoryview(self.content)

    def __copy__(self):
        # BinaryValue is immutable from the point of view of the API.
        return self

    def __deepcopy__(self, memo):
        return self.__copy__()

    def to_base64(self) -> str:
        """Encode to a base64 string."""
        return base64.b64encode(self).decode()

    def decode(self, encoding="utf-8", errors="strict") -> str:
        """Decode the raw contents to a string."""
        return self.content.decode(encoding, errors)

    @staticmethod
    def from_bytes(data: Buffer):
        """Create a BinaryValue from bytes."""
        data = bytes(data)
        if not data:
            return _EMPTY_BINARY_DATA
        return BinaryBytes(data)

    @staticmethod
    def from_file(path: str, *, filter_ext=(), reader: io.FileIO | None = None):
        """ Open a file as a binary value.

        :param path: path to the file
        :param filter_ext: passed to `file_open` function
        :param reader: if set, use it instead of opening; path must match the name
        :raise OSError: if the file cannot be opened
        """
        if reader is None:
            reader = file_open(path, 'rb', filter_ext=filter_ext)
        else:
            assert reader.name == path, "reader.name must match the path"
        return BinaryFile(reader)


class BinaryBytes(BinaryValue):
    """Static binary value."""
    __slots__ = ('__data',)

    def __init__(self, data: Buffer):
        # force bytes
        self.__data = bytes(data)

    @property
    def content(self):
        return self.__data

    def __bool__(self):
        return bool(self.__data)

    def __repr__(self):
        data = self.__data
        if len(data) > 27:
            data = data[:27] + b'...'
        return f"Binary:{data!r}"


class BinaryFile(BinaryValue):
    """Lazy loaded file."""
    __slots__ = ('__content', '__file', '__mimetype')

    def __init__(self, file: io.FileIO):
        # __content is None <=> the file is open
        self.__content: bytes | None = None
        self.__file = file
        assert file.mode == 'rb' and not file.closed and file.seekable(), "file needs to be opened in 'rb' mode"
        self.__mimetype: str | None = None

    def open(self):
        if self.__content is not None:
            return io.BytesIO(self.__content)
        # reopen the file
        # cannot use `os.dup`, it shares the file pointer (POSIX)
        reader = self.__file
        return open(reader.name, 'rb')

    @property
    def content(self) -> bytes:
        if self.__content is None:
            reader = self.__file
            reader.seek(0)
            self.__content = reader.read()
            reader.close()  # not needed anymore
        return self.__content

    @property
    def mimetype(self):
        if self.__mimetype is None:
            if self.__content is not None:
                self.__mimetype = BinaryBytes(self.__content).mimetype
            else:
                from .mimetypes import guess_file_mimetype  # noqa: PLC0415
                self.__mimetype = guess_file_mimetype(self.local_path)
        return self.__mimetype

    @property
    def size(self):
        if self.__content is not None:
            return len(self.__content)
        return os.fstat(self.__file.fileno()).st_size

    @property
    def local_path(self):
        return self.__file.name

    def close(self):
        self.__file.close()

    def __del__(self):
        self.close()

    def __copy__(self):
        if self.__content is None:
            assert not self.__file.closed
            return BinaryFile(os.fdopen(os.dup(self.__file.fileno()), 'rb'))
        return super().__copy__()

    def __repr__(self):
        return f"Binary({self.local_path!r})"


_EMPTY_BINARY_DATA = BinaryBytes(b'')
