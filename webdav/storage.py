import os
from django.conf import settings


class FSStorage:
    chunk_size = 32768

    def __init__(self, home=None):
        self.home = home or settings.WEBDAV_STORAGE_PATH

    def store_string(self, content, resource):
        directory = os.path.join(self.home, str(resource.user.pk))
        os.makedirs(directory, exist_ok=True)  # Ensure directory exists

        filename = os.path.join(directory, str(resource.uuid))
        try:
            with open(filename, 'wb') as f:  # Open in binary mode
                f.write(content)
        except IOError as e:
            raise e

    def store(self, request, resource):
        directory = os.path.join(self.home, str(resource.user.pk))
        os.makedirs(directory, exist_ok=True)  # Ensure directory exists

        filename = os.path.join(directory, str(resource.uuid))
        try:
            with open(filename, 'wb') as f:  # Open in binary mode
                cl = int(resource.size)
                while cl > 0:
                    chunk = request.read(min(cl, self.chunk_size))
                    if not chunk:
                        break
                    f.write(chunk)
                    cl -= len(chunk)
        except IOError as e:
            raise e

    def delete(self, resource):
        filename = os.path.join(self.home, str(resource.user.pk), str(resource.uuid))
        if os.path.exists(filename):
            os.remove(filename)

    def retrieve(self, resource):

        class FSIterable:

            def __init__(self, path, size, chunk_size):
                self.file = open(path, 'rb')  # Open in binary mode
                self.size = size
                self.chunk_size = chunk_size

            def __iter__(self):
                return self

            def __next__(self):
                if self.size <= 0:
                    self.file.close()  # Ensure file is closed after iteration
                    raise StopIteration
                chunk = self.file.read(min(self.size, self.chunk_size))
                self.size -= len(chunk)
                return chunk

        filename = os.path.join(self.home, str(resource.user.pk), str(resource.uuid))
        return FSIterable(filename, resource.size, self.chunk_size)

    def retrieve_string(self, resource):
        return ''.join(chunk.decode('utf-8') for chunk in self.retrieve(resource))

    def exists(self, resource):
        filename = os.path.join(self.home, str(resource.user.pk), str(resource.uuid))
        return os.path.exists(filename)
